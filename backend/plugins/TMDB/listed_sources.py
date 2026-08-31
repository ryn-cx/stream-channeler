# TODO: Validate
"""Reading a title into every service that lists it."""

from __future__ import annotations

import uuid

from loguru import logger

from app.shows.models import Show
from app.unmatched_sources.service import (
    clear_unmatched_source,
    record_unmatched_source,
)
from plugins.TMDB.keys import parse_show_key
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.media_info import (
    Provider,
    plugin_for_tmdb_name,
    streaming_providers,
)
from plugins.TMDB.upsert import UpsertMixin
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
)
from plugins.utils.manage_plugins import plugin_for_url

# from plugins.WatchMode import WatchMode  # noqa: ERA001


# TODO: Validate
class ListedSourcesMixin(UpsertMixin, LookupMixin):
    # TODO: Validate
    def _import_listed_sources(
        self,
        show_key: str,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        """Import the title from every service Watchmode or JustWatch lists it on.

        Both name each service by a link to the title on it, so the listing a
        website carries is reached by the address of that listing first. A
        service listed without a usable address is searched for the title's name
        on its own website instead, and the closest result taken.

        An address a plugin turns out not to be able to import is passed over
        rather than raised on. Both lookups list a service that sells a disc of
        the title the same way they list one that streams it, and an address
        like that is a shop page rather than a listing anything watches.
        """
        media_type, tmdb_id = parse_show_key(show_key)
        providers_file = self.watch_providers_file(media_type, tmdb_id)
        providers_file.download_if_outdated()
        providers = streaming_providers(providers_file.parsed())

        imported: set[type[AbstractPlugin]] = set()
        if providers:
            noted = self._linked_show_ids(show)
            linked = self._linked_plugin_keys(show)
            for url in self._listed_source_urls(show_key):
                plugin_class = plugin_for_url(url)
                if plugin_class is None or plugin_class.plugin_name() in linked:
                    continue
                if not self._import_child_url(plugin_class, url, show, force=force):
                    continue
                self._note_new_links(show, noted, "Automatic: Watchmode listing")
                imported.add(plugin_class)

        self._import_searched_sources(providers, show, imported, force=force)

    # TODO: Validate
    def _linked_show_ids(self, show: Show) -> set[uuid.UUID]:
        self.session.flush()
        self.session.expire(show, ["non_canonical_shows"])
        return {link.show_id for link in show.non_canonical_shows}

    # TODO: Validate
    def _linked_plugin_keys(self, show: Show) -> set[str]:
        self.session.flush()
        self.session.expire(show, ["non_canonical_shows"])
        return {link.show.source.plugin.key for link in show.non_canonical_shows}

    # TODO: Validate
    def _note_new_links(
        self,
        show: Show,
        noted: set[uuid.UUID],
        note: str,
    ) -> None:
        self.session.flush()
        self.session.expire(show, ["non_canonical_shows"])
        for link in show.non_canonical_shows:
            if link.show_id in noted:
                continue
            link.note = note
            self.session.add(link)
            noted.add(link.show_id)

    # TODO: Validate
    def _import_searched_sources(
        self,
        providers: list[Provider],
        show: Show,
        imported: set[type[AbstractPlugin]],
        *,
        force: bool = False,
    ) -> None:
        noted = self._linked_show_ids(show)
        linked = self._linked_plugin_keys(show)
        for provider in providers:
            plugin_class = plugin_for_tmdb_name(provider.provider_name)
            already_linked = (
                plugin_class is not None and plugin_class.plugin_name() in linked
            )
            if (
                plugin_class in imported
                or already_linked
                or self._import_searched_source(plugin_class, show, force=force)
            ):
                if plugin_class is not None:
                    imported.add(plugin_class)
                self._note_new_links(
                    show,
                    noted,
                    "Automatic: Source website search",
                )
                clear_unmatched_source(self.session, show.id, provider.provider_name)
                continue

            record_unmatched_source(
                self.session,
                show.id,
                provider.provider_name,
                plugin_class.plugin_name() if plugin_class else None,
            )

    # TODO: Validate
    def _import_searched_source(
        self,
        plugin_class: type[AbstractPlugin] | None,
        show: Show,
        *,
        force: bool = False,
    ) -> bool:
        if (
            plugin_class is None
            or not plugin_class.implements("search")
            or not show.name
        ):
            return False

        url = self._searched_source_url(plugin_class, show.name)
        if url is None:
            return False

        return self._import_child_url(plugin_class, url, show, force=force)

    # TODO: Validate
    def _searched_source_url(
        self,
        plugin_class: type[AbstractPlugin],
        name: str,
    ) -> str | None:
        savepoint = self.session.begin_nested()
        try:
            url = plugin_class(self.session).search(name)
        except Exception:  # noqa: BLE001
            savepoint.rollback()
            logger.exception("Searching {} for {}", plugin_class.plugin_name(), name)
            return None
        savepoint.commit()
        return url

    # TODO: Validate
    def _import_child_url(
        self,
        plugin_class: type[AbstractPlugin],
        url: str,
        show: Show,
        *,
        force: bool = False,
    ) -> bool:
        savepoint = self.session.begin_nested()
        try:
            plugin_class(self.session).import_url(url, show, force=force)
        except InvalidURLError:
            savepoint.rollback()
            logger.info("Nothing to import at {}", url)
            return False
        except Exception:  # noqa: BLE001
            savepoint.rollback()
            logger.exception("Importing {}", url)
            return False
        savepoint.commit()
        return True

    # TODO: Validate
    def _listed_source_urls(self, show_key: str) -> list[str]:  # noqa: ARG002
        """Return every address either lookup gives for the title, without repeats."""
        # media_type, tmdb_id = parse_show_key(show_key)  # noqa: ERA001
        # return WatchMode(self.session).source_urls(media_type, tmdb_id)  # noqa: ERA001
        return []
