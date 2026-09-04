# TODO: Validate
"""Reading a title into every service that lists it."""

from __future__ import annotations

import uuid

from loguru import logger

from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from app.sources.service.unmatched import (
    clear_unmatched_source,
    record_unmatched_source,
)
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.media_info import (
    plugin_for_tmdb_name,
    streaming_providers,
)
from plugins.TMDB.watch_provider_sync import WatchProviderSyncMixin
from plugins.utils.abstract_plugin import AbstractPlugin, MediaNotFoundError


# TODO: Validate
class ListedSourcesMixin(WatchProviderSyncMixin, LookupMixin):
    # TODO: Validate
    def _import_media_from_other_websites(self, show_key: str, show: Show) -> None:
        """Import the media using the other plugins if it is available on that websites."""
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        providers = streaming_providers(
            self.watch_providers_file(media_type, tmdb_id).parsed(),
        )
        imported: set[type[AbstractPlugin]] = set()
        noted = self.non_canonical_show_ids(show)
        linked = self.plugins_with_non_canonical_shows(show)
        for provider in providers:
            plugin_class = plugin_for_tmdb_name(provider.provider_name)

            # If there is no matching plugin the website name is logged into the
            # database for helping determine what websites to support in the future.
            if plugin_class is None:
                record_unmatched_source(
                    self.session,
                    show.id,
                    provider.provider_name,
                    None,
                )
                continue

            # Some websites are basically listed multiple times on TMDB. For
            # example, Amazon may have multiple names like "Amazon Prime
            # Video", and "Amazon Prime Video with Ads".
            has_listing = (
                plugin_class in imported or plugin_class.plugin_name() in linked
            )
            if not has_listing:
                has_listing = self._import_searched_source(
                    plugin_class,
                    show,
                    media_type,
                )

            if not has_listing:
                record_unmatched_source(
                    self.session,
                    show.id,
                    provider.provider_name,
                    plugin_class.plugin_name(),
                )
                continue

            imported.add(plugin_class)
            self._note_new_links(
                show,
                noted,
                "Automatic: Source website search",
            )
            clear_unmatched_source(self.session, show.id, provider.provider_name)

    # TODO: Validate
    def non_canonical_show_ids(self, show: Show) -> set[uuid.UUID]:
        self.session.flush()
        self.session.expire(show, ["non_canonical_shows"])
        return {link.show_id for link in show.non_canonical_shows}

    # TODO: Validate
    def plugins_with_non_canonical_shows(self, show: Show) -> set[str]:
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
    def _import_searched_source(
        self,
        plugin_class: type[AbstractPlugin],
        show: Show,
        media_type: TMDBMediaType,
    ) -> bool:
        if not plugin_class.implements("search_for_url") or not show.name:
            return False

        savepoint = self.session.begin_nested()
        try:
            plugin_class(self.session).import_by_name(
                [show.name],
                show,
                media_type,
                show.year,
            )
        except MediaNotFoundError:
            savepoint.rollback()
            logger.info(
                "{} carries no title named {}",
                plugin_class.plugin_name(),
                show.name,
            )
            return False
        except Exception:  # noqa: BLE001
            savepoint.rollback()
            logger.exception(
                "Failed to import {} from {}",
                show.name,
                plugin_class.plugin_name(),
            )
            return False
        savepoint.commit()
        return True
