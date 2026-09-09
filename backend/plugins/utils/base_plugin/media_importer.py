# TODO: Validate
from __future__ import annotations

from abc import ABC
from functools import singledispatchmethod
from typing import TYPE_CHECKING

from app.titles.models import Title
from plugins.utils.base_plugin.url import BaseURLMixin

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.media.media_type import TMDBMediaType
    from app.seasons.models import Season
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.importer import BaseImporter


class BaseMediaImporterMixin(BaseURLMixin, ABC):
    if TYPE_CHECKING:
        # TODO: Validate
        def search_for_title_url(
            self,
            names: list[str],
            media_type: TMDBMediaType,
            year: int | None = None,
        ) -> str | None: ...

    # TODO: Validate
    def validate_and_import_url(self, url: str) -> list[URLImportResult]:
        self._validate_url(url)
        return self._media_importer(url).import_url(url)

    # TODO: Validate
    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> list[URLImportResult]:
        url = self.search_for_title_url(names, media_type, year)
        if url:
            return self.validate_and_import_url(url)
        return []

    # TODO: Validate
    def update_title(self, title: Title, *, force: bool = False) -> None:
        self._media_importer(title).update_title(title, force=force)

    # TODO: Validate
    def update_season(self, season: Season) -> None:
        self._media_importer(season.title).update_season(season)

    # TODO: Validate
    def update_episode(self, episode: Episode) -> None:
        self._media_importer(episode.season.title).update_episode(
            episode,
        )

    # TODO: Validate
    def on_update_title_failure(self, title: Title, error: Exception) -> None:
        self._media_importer(title).on_update_failure(title, error)

    # TODO: Validate
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self._media_importer(season.title).on_update_failure(season, error)

    # TODO: Validate
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self._media_importer(episode.season.title).on_update_failure(
            episode,
            error,
        )

    # TODO: Validate
    @singledispatchmethod
    def _media_importer(self, url_or_title: str | Title) -> BaseImporter:  # noqa: ARG002
        raise TypeError

    # TODO: Validate
    @_media_importer.register(str)
    def _(self, url: str) -> BaseImporter:
        return self._media_importer_from_url(url)

    # TODO: Validate
    @_media_importer.register(Title)
    def _(self, title: Title) -> BaseImporter:
        return self._media_importer_from_title(title)

    # TODO: Validate
    def _media_importer_from_url(self, url: str) -> BaseImporter:  # noqa: ARG002
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    # TODO: Validate
    def _media_importer_from_title(self, title: Title) -> BaseImporter:  # noqa: ARG002
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]
