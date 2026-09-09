from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from plugins.utils.base_plugin.url import BaseURLMixin

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.media.media_type import TMDBMediaType
    from app.seasons.models import Season
    from app.titles.models import Title
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.importer import BaseImporter


class BaseMediaImporterMixin(BaseURLMixin, ABC):
    if TYPE_CHECKING:

        def search_for_title_url(
            self,
            names: list[str],
            media_type: TMDBMediaType,
            year: int | None = None,
        ) -> str | None:
            """Search for a title and return its URL if found."""

    # TODO: Validate
    def validate_and_import_url(self, url: str) -> list[URLImportResult]:
        """Validate the given URL and import it using the appropriate media importer."""
        self._validate_url(url)
        return self._media_importer(url).import_url(url)

    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> list[URLImportResult]:
        """Search for a title URL and import it if found."""
        if url := self.search_for_title_url(names, media_type, year):
            return self.validate_and_import_url(url)
        return []

    def update_title(self, title: Title, *, force: bool = False) -> None:
        """"""
        self._media_importer(title).update_title(title, force=force)

    def update_season(self, season: Season) -> None:
        self._media_importer(season.title).update_season(season)

    def update_episode(self, episode: Episode) -> None:
        self._media_importer(episode.season.title).update_episode(episode)

    def on_update_title_failure(self, title: Title, error: Exception) -> None:
        self._media_importer(title).on_update_failure(title, error)

    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self._media_importer(season.title).on_update_failure(season, error)

    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self._media_importer(episode.season.title).on_update_failure(episode, error)

    # TODO: Validate
    def _media_importer(self, url_or_title: str | Title) -> BaseImporter:
        if isinstance(url_or_title, str):
            return self._media_importer_from_url(url_or_title)
        return self._media_importer_from_title(url_or_title)

    # TODO: Validate
    def _media_importer_from_url(self, url: str) -> BaseImporter:  # noqa: ARG002
        """Return the media importer to use for the given URL."""
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    # TODO: Validate
    def _media_importer_from_title(self, title: Title) -> BaseImporter:  # noqa: ARG002
        """Return the media importer to usefor the given title."""
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]
