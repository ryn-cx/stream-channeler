# TODO: Validate
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from loguru import logger
from sqlmodel import select

from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from app.shows.service.canonical import match_show_to_tmdb
from app.sources.models import UnmatchedSource
from app.sources.service.unmatched import remove_unmatched_source
from plugins.TMDB.files import MoviesWatchProviders, TVSeriesWatchProviders
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.shared import TMDBShared
from plugins.TMDB.utils import get_media_plugin, streaming_providers
from plugins.utils.abstract_plugin import AbstractPlugin, MediaNotFoundError


# TODO: Validate
class TMDBExternalWebsites(TMDBShared, ABC):
    """Functions for importing TMDB titles on external websites."""

    @abstractmethod
    def _provider_file(
        self,
        show_key: str,
    ) -> MoviesWatchProviders | TVSeriesWatchProviders: ...

    # TODO: Validate
    def _import_title_from_external_websites(self, show_key: str, show: Show) -> None:
        """Import the title from all external websites."""
        # TODO: TMDB should have a special Show object that makes empty names
        # impossible.
        if not show.name:
            msg = f"{show} has no name to search other websites with."
            raise ValueError(msg)

        media_type, _ = get_media_type_and_tmdb_id(show_key)
        plugins_with_non_canonical_shows = self.plugins_with_non_canonical_shows(show)
        for provider in streaming_providers(self._provider_file(show_key).parsed()):
            media_plugin = get_media_plugin(provider.provider_name)

            # If there is no matching plugin the website's name is logged into the
            # database to help determine what websites to support in the future.
            if media_plugin is None:
                self._upsert_unmatched_source(show.id, provider.provider_name, None)
                continue

            if self.external_link_exists(
                media_plugin=media_plugin,
                show=show,
                name=show.name,
                media_type=media_type,
                plugins_with_non_canonical_shows=plugins_with_non_canonical_shows,
            ):
                plugins_with_non_canonical_shows.add(media_plugin.plugin_name())
                # This will clear out records for new/updated plugins and entries for
                # shows that where manually linked to TMDB.
                remove_unmatched_source(self.session, show.id, provider.provider_name)
            else:
                self._upsert_unmatched_source(
                    show_id=show.id,
                    provider_name=provider.provider_name,
                    plugin_key=media_plugin.plugin_name(),
                )

    def _upsert_unmatched_source(
        self,
        show_id: uuid.UUID,
        provider_name: str,
        plugin_key: str | None,
    ) -> None:
        statement = select(UnmatchedSource).where(
            UnmatchedSource.show_id == show_id,
            UnmatchedSource.provider_name == provider_name,
        )
        if self.session.exec(statement).one_or_none() is not None:
            return

        self.session.add(
            UnmatchedSource(
                show_id=show_id,
                provider_name=provider_name,
                plugin_key=plugin_key,
            ),
        )
        self.session.commit()

    # TODO: Validate
    def external_link_exists(
        self,
        media_plugin: type[AbstractPlugin],
        show: Show,
        name: str,
        media_type: TMDBMediaType,
        plugins_with_non_canonical_shows: set[str],
    ) -> bool:
        return (
            media_plugin.plugin_name() in plugins_with_non_canonical_shows
            or self._import_external_plugin(
                plugin_class=media_plugin,
                show=show,
                name=name,
                media_type=media_type,
                year=show.year,
            )
        )

    # TODO: Validate
    def plugins_with_non_canonical_shows(self, show: Show) -> set[str]:
        self.session.flush()
        self.session.expire(show, ["non_canonical_shows"])
        return {
            link.non_canonical_show.source.plugin.key
            for link in show.non_canonical_show_links
        }

    # TODO: Validate
    def _import_external_plugin(
        self,
        plugin_class: type[AbstractPlugin],
        show: Show,
        name: str,
        media_type: TMDBMediaType,
        year: int | None,
    ) -> bool:
        if not plugin_class.implements("search_for_url"):
            return False

        plugin = plugin_class(self.session)
        savepoint = self.session.begin_nested()
        try:
            results = plugin.import_by_name([name], media_type, year)
            for imported_show in plugin.imported_shows(results):
                match_show_to_tmdb(
                    self.session,
                    imported_show,
                    show,
                    f"Automatic: {show.media_type} {show.name} ({show.year}) was found "
                    f"on {plugin_class.plugin_name()}.",
                )
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
