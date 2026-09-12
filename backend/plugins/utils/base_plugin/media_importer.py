from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from plugins.utils.abstract_plugin import AbstractPlugin, URLImportResult
from plugins.utils.base_plugin.url import BaseURLMixin

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.plugins.models import Plugin
    from app.seasons.models import Season
    from app.titles.models import Title
    from plugins.utils.base_plugin.importer import BaseImporter


class BaseMediaImporterMixin(BaseURLMixin, AbstractPlugin, ABC):
    plugin: Plugin

    @override
    def validate_and_import_url(self, url: str) -> list[URLImportResult]:
        media_importer = self._media_importer(url)
        media_importer.validate_url(url)
        return media_importer.import_url(url)

    @override
    def update_title(self, title: Title, *, force: bool = False) -> None:
        self._media_importer(title).update_title(title, force=force)

    @override
    def update_season(self, season: Season) -> None:
        self._media_importer(season.title).update_season(season)

    @override
    def update_episode(self, episode: Episode) -> None:
        self._media_importer(episode.season.title).update_episode(episode)

    @override
    def on_update_title_failure(self, title: Title, error: Exception) -> None:
        self._media_importer(title).on_update_failure(title, error)

    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self._media_importer(season.title).on_update_failure(season, error)

    @override
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self._media_importer(episode.season.title).on_update_failure(episode, error)

    def _media_importer(self, url_or_title: str | Title) -> BaseImporter:
        """Return the appropriate media importer based on the url or title."""
        if isinstance(url_or_title, str):
            return self._media_importer_from_url(url_or_title)
        return self._media_importer_from_title(url_or_title)

    def _media_importer_from_url(self, url: str) -> BaseImporter:  # noqa: ARG002
        """Return the media importer to use for the given URL."""
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    def _media_importer_from_title(self, title: Title) -> BaseImporter:  # noqa: ARG002
        """Return the media importer to usefor the given title."""
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]
