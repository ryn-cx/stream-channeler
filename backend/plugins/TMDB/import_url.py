# TODO: Validate
"""Reading a title in, whether a URL named it or an id did."""

from __future__ import annotations

import uuid
from typing import Any, override

from loguru import logger

from app.media.media_type import MediaType
from app.shows.models import Show
from app.unmatched_sources.service import (
    clear_unmatched_source,
    record_unmatched_source,
)
from plugins.TMDB.constants import media_url
from plugins.TMDB.keys import parse_show_key, show_key
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.media_info import (
    Provider,
    plugin_for_tmdb_name,
    streaming_providers,
)
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import TMDBURLHandler
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin
from plugins.utils.base_plugin.url import URLHandler
from plugins.utils.manage_plugins import plugin_for_url
from plugins.WatchMode import WatchMode


# TODO: Validate
class ImportURLMixin(
    UpsertMixin,
    LookupMixin,
    URLHandlerPlugin[TMDBURLHandler],
    register=False,
):
    # TODO: Validate
    @override
    def _import_handler(
        self,
        handler: URLHandler[Any],
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = handler.show_key
        stored = self._preload_show(show_key).one_or_none()
        if stored and not force:
            return handler.import_results(stored)

        # This title's own rows are written before anything is handed on. A
        # website's plugin resolves the title it carries by asking TMDB for it,
        # so a hand-off made first would be asking for a title that is not
        # stored yet and would send the import straight back round; made after,
        # that ask is answered by the row written here and the chain ends.
        self._download_title_files(show_key)
        show = self.upsert_show(self.source, show_key, force=force)

        if canonical_show is None:
            self._import_listed_sources(show_key, show, force=force)

        return handler.import_results(show)

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
        website carries is reached by the address of that listing rather than by
        searching the website for the title's name and taking whichever result
        looks closest.

        An address a plugin turns out not to be able to import is passed over
        rather than raised on. Both lookups list a service that sells a disc of
        the title the same way they list one that streams it, and an address
        like that is a shop page rather than a listing anything watches.
        """
        media_type, tmdb_id = parse_show_key(show_key)
        providers = streaming_providers(
            self.watch_providers_file(media_type, tmdb_id).parsed(),
        )

        imported: set[type[AbstractPlugin]] = set()
        if providers:
            noted = self._linked_show_ids(show)
            linked = self._linked_plugin_keys(show)
            for url in self._listed_source_urls(show_key):
                plugin_class = plugin_for_url(url)
                if plugin_class is None or plugin_class.plugin_key() in linked:
                    continue
                if not self._import_child_url(plugin_class, url, show, force=force):
                    continue
                self._note_new_links(show, noted, "Automatic: Watchmode listing")
                imported.add(plugin_class)

        self._record_unmatched_sources(providers, show, imported)

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
            link.show.canonical_show_note = note
            self.session.add(link.show)
            noted.add(link.show_id)

    # TODO: Validate
    def _record_unmatched_sources(
        self,
        providers: list[Provider],
        show: Show,
        imported: set[type[AbstractPlugin]],
    ) -> None:
        linked = self._linked_plugin_keys(show)
        for provider in providers:
            plugin_class = plugin_for_tmdb_name(provider.provider_name)
            already_linked = (
                plugin_class is not None and plugin_class.plugin_key() in linked
            )
            if plugin_class in imported or already_linked:
                if plugin_class is not None:
                    imported.add(plugin_class)
                clear_unmatched_source(
                    self.session,
                    show.id,
                    provider.provider_name,
                )
                continue

            record_unmatched_source(
                self.session,
                show.id,
                provider.provider_name,
                plugin_class.plugin_key() if plugin_class else None,
            )

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
    def _listed_source_urls(self, show_key: str) -> list[str]:
        """Return every address either lookup gives for the title, without repeats."""
        media_type, tmdb_id = parse_show_key(show_key)
        return WatchMode(self.session).source_urls(media_type, tmdb_id)

    # TODO: Validate
    def _download_title_files(self, show_key: str) -> None:
        """Read the title's own file and its seasons', and nothing below them.

        A season carries every episode of it, which is all an upsert here reads,
        so the episode files are left alone. They are two downloads apiece and a
        title runs to hundreds of them; what wants one - matching a website's
        episode to TMDB's - asks for it when it gets there.
        """
        _cache = self._preload_show_files(show_key)
        self._download_outdated_files(self._show_files(show_key))
        for season_key in self._season_keys_from_file(show_key):
            self._download_outdated_files(self._season_files(season_key, show_key))

    # TODO: Validate
    def import_search(
        self,
        name: str,
        media_type: MediaType | None = None,
        year: int | None = None,
        *,
        force: bool = False,
    ) -> Show | None:
        """Import the first title TMDB returns for `name`.

        `media_type` narrows the search to one half of the catalogue and `year`
        to when the title came out. Neither is required: a search of both halves
        takes whichever half the first result turned out to be from.

        Returns None when TMDB has nothing under that name, since a name is a
        guess at a title in a way an id is not.
        """
        found = self._first_search_result(name, media_type, year)
        if found is None:
            return None

        half, tmdb_id = found
        if half == MediaType.movie:
            return self.import_movie(tmdb_id, force=force)
        return self.import_show(tmdb_id, force=force)

    # TODO: Validate
    def _first_search_result(
        self,
        name: str,
        media_type: MediaType | None,
        year: int | None,
    ) -> tuple[MediaType, int] | None:
        """Return which half the first title TMDB returns is from, and its id."""
        if media_type is not None:
            results = self.search_media(media_type, name, year).parsed().results
            return (media_type, results[0].id) if results else None

        # A search of both halves also returns people, who are no title and are
        # passed over rather than taken as the first result.
        for result in self.search_media(None, name, year).parsed().results:
            # Which half of the catalogue a search of both says a result came
            # from. A multi search also returns people, who are no title and
            # cannot be imported.
            half = {"movie": MediaType.movie, "tv": MediaType.tv}.get(
                result.media_type,
            )
            if half is not None:
                return half, result.id
        return None

    # TODO: Validate
    def import_show(self, tmdb_id: int, *, force: bool = False) -> Show:
        """Import a TMDB tv entry using a tmdb_id."""
        self.import_url(media_url(MediaType.tv, tmdb_id), force=force)
        return self._preload_show(show_key(MediaType.tv, tmdb_id)).one()

    # TODO: Validate
    def import_movie(self, tmdb_id: int, *, force: bool = False) -> Show:
        """Import a TMDB movie entry using a tmdb_id."""
        self.import_url(media_url(MediaType.movie, tmdb_id), force=force)
        return self._preload_show(show_key(MediaType.movie, tmdb_id)).one()
