# TODO: Validate
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from loguru import logger
from sqlmodel import select

from app.canonical_media.tmdb import (
    get_media_type_and_tmdb_id,
)
from app.media.media_type import TMDBMediaType
from app.sources.models import UnmatchedSource
from app.sources.service.unmatched import remove_unmatched_source
from app.titles.models import Title
from app.titles.service.linking import link_title_to_tmdb
from plugins.TMDB.files import MoviesWatchProviders, TVSeriesWatchProviders
from plugins.TMDB.shared import TMDBShared
from plugins.TMDB.utils import (
    get_media_plugin,
    streaming_providers,
)
from plugins.utils.abstract_plugin import AbstractPlugin, MediaNotFoundError


# TODO: Validate
class TMDBExternalWebsites(TMDBShared, ABC):
    """Functions for importing TMDB titles on external websites."""

    # TODO: Validate
    @abstractmethod
    def _provider_file(
        self,
        title_key: str,
    ) -> MoviesWatchProviders | TVSeriesWatchProviders: ...

    """Return the provider file for the given title key."""

    # TODO: Validate
    def link_title_to_websites(self, title: Title) -> None:
        """Import the title from all external websites."""
        # TODO: TMDB should have a special Title object that makes empty names
        # impossible.
        if not title.name:
            msg = f"{title} has no name to search other websites with."
            raise ValueError(msg)

        media_type, _ = get_media_type_and_tmdb_id(title.key)
        plugins_with_non_canonical_titles = self.plugins_with_non_canonical_titles(
            title,
        )
        provider_file = self._provider_file(title.key)
        provider_file.download_if_outdated()
        for provider in streaming_providers(provider_file.parsed()):
            media_plugin = get_media_plugin(provider.provider_name)

            # If there is no matching plugin the website's name is logged into the
            # database to help determine what websites to support in the future.
            if media_plugin is None:
                self._upsert_unmatched_source(title.id, provider.provider_name, None)
                continue

            if self.external_link_exists(
                media_plugin=media_plugin,
                title=title,
                name=title.name,
                media_type=media_type,
                plugins_with_non_canonical_titles=plugins_with_non_canonical_titles,
            ):
                plugins_with_non_canonical_titles.add(media_plugin.plugin_name())
                # This will clear out records for new/updated plugins and entries for
                # titles that where manually linked to TMDB.
                remove_unmatched_source(self.session, title.id, provider.provider_name)
            else:
                self._upsert_unmatched_source(
                    title_id=title.id,
                    provider_name=provider.provider_name,
                    plugin_key=media_plugin.plugin_name(),
                )

    # TODO: Validate
    def _upsert_unmatched_source(
        self,
        title_id: uuid.UUID,
        provider_name: str,
        plugin_key: str | None,
    ) -> None:
        """Upsert a source that is listed on TMDB but could not be imported."""
        statement = select(UnmatchedSource).where(
            UnmatchedSource.title_id == title_id,
            UnmatchedSource.provider_name == provider_name,
        )
        if self.session.exec(statement).one_or_none() is not None:
            return

        self.session.add(
            UnmatchedSource(
                title_id=title_id,
                provider_name=provider_name,
                plugin_key=plugin_key,
            ),
        )
        self.session.flush()

    # TODO: Validate
    def external_link_exists(
        self,
        media_plugin: type[AbstractPlugin],
        title: Title,
        name: str,
        media_type: TMDBMediaType,
        plugins_with_non_canonical_titles: set[str],
    ) -> bool:
        return (
            # The external link can already exist.
            media_plugin.plugin_name() in plugins_with_non_canonical_titles
            # Or the external link can be made right now.
            or self._import_external_plugin(
                plugin_class=media_plugin,
                title=title,
                name=name,
                media_type=media_type,
                year=title.year,
            )
        )

    # TODO: Validate
    def plugins_with_non_canonical_titles(self, title: Title) -> set[str]:
        # TODO: Is flush/expire still needed?
        self.session.flush()
        self.session.expire(title, ["non_canonical_title_links"])
        return {
            link.non_canonical_title.source.plugin.key
            for link in title.non_canonical_title_links
        }

    # TODO: Validate
    def _import_external_plugin(
        self,
        plugin_class: type[AbstractPlugin],
        title: Title,
        name: str,
        media_type: TMDBMediaType,
        year: int | None,
    ) -> bool:
        if not plugin_class.implements("search_for_url"):
            return False

        plugin = plugin_class(self.session)
        savepoint = self.session.begin_nested()
        try:
            results = plugin.import_search([name], media_type, year)
            for result in results:
                link_title_to_tmdb(
                    self.session,
                    result.title,
                    title,
                    f"Automatic: {title.media_type} {title.name} ({title.year}) was found "
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
