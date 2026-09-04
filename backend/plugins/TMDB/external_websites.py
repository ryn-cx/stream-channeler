# TODO: Validate
from __future__ import annotations

import uuid

from loguru import logger

from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from app.sources.service.unmatched import (
    clear_unmatched_source,
    upsert_unmatched_source,
)
from plugins.TMDB.files import MoviesWatchProviders, TVSeriesWatchProviders
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.shared import TMDBShared
from plugins.TMDB.utils import get_external_plugin, streaming_providers
from plugins.utils.abstract_plugin import AbstractPlugin, MediaNotFoundError


# TODO: Validate
class TMDBExternalWebsites(TMDBShared):
    """Functions for importing TMDB titles on external websites."""

    # TODO: Validate
    def _provider_file(
        self,
        show_key: str,
    ) -> MoviesWatchProviders | TVSeriesWatchProviders:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        if media_type == TMDBMediaType.movie:
            return self.latest_movies_watch_providers_file(tmdb_id)
        return self.latest_tv_series_watch_providers_file(tmdb_id)

    # TODO: Validate
    def _import_title_from_external_websites(self, show_key: str, show: Show) -> None:
        """Import the title from external websites."""
        # TODO: TMDB should have a special Show object that makes empty names
        # impossible.
        if not show.name:
            msg = f"{show} has no name to search other websites with."
            raise ValueError(msg)

        media_type, _ = get_media_type_and_tmdb_id(show_key)
        providers = streaming_providers(self._provider_file(show_key).parsed())
        non_canonical_show_ids = self.non_canonical_show_ids(show)
        plugins_with_non_canonical_shows = self.plugins_with_non_canonical_shows(show)
        for provider in providers:
            external_plugin = get_external_plugin(provider.provider_name)

            # If there is no matching plugin the website name is logged into the
            # database to help determine what websites to support in the future.
            if not (
                external_plugin
                and self.external_link_exists(
                    external_plugin,
                    show,
                    show.name,
                    media_type,
                    plugins_with_non_canonical_shows,
                )
            ):
                upsert_unmatched_source(
                    self.session,
                    show.id,
                    provider.provider_name,
                    external_plugin.plugin_name() if external_plugin else None,
                )
                continue

            plugins_with_non_canonical_shows.add(external_plugin.plugin_name())
            self._note_new_links(
                show,
                non_canonical_show_ids,
                f"Automatic: {show.media_type} {show.name} ({show.year}) was found on {self.plugin_name()}.",
            )
            clear_unmatched_source(self.session, show.id, provider.provider_name)

    # TODO: Validate
    def external_link_exists(
        self,
        external_plugin: type[AbstractPlugin],
        show: Show,
        name: str,
        media_type: TMDBMediaType,
        plugins_with_non_canonical_shows: set[str],
    ) -> bool:
        return (
            external_plugin.plugin_name() in plugins_with_non_canonical_shows
            or self._import_searched_source(
                external_plugin,
                show,
                name,
                media_type,
                show.year,
            )
        )

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

    def _import_searched_source(
        self,
        plugin_class: type[AbstractPlugin],
        show: Show,
        name: str,
        media_type: TMDBMediaType,
        year: int | None,
    ) -> bool:
        if not plugin_class.implements("search_for_url"):
            return False

        savepoint = self.session.begin_nested()
        try:
            plugin_class(self.session).import_by_name([name], show, media_type, year)
        except MediaNotFoundError:
            savepoint.rollback()
            logger.info("Could not find {} on {}", name, plugin_class.plugin_name())
            return False
        except Exception:  # noqa: BLE001
            savepoint.rollback()
            logger.exception(
                "Failed to import {} from {}",
                name,
                plugin_class.plugin_name(),
            )
            return False
        savepoint.commit()
        return True
