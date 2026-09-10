from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.base import BasePlugin

if TYPE_CHECKING:
    from app.titles.models import Title
    from plugins.utils.base_plugin.url import ParsedURL


class BaseImporter(BasePlugin, ABC):
    # TODO: Validate
    def validate_url(self, url: str) -> None:  # noqa: ARG002
        return

    def parse_url(self, url: str) -> ParsedURL:
        """Return information about the title extracted from the URL.

        In some situations this may require network requests."""
        msg = f"{self.plugin_name()} does not implement get_media_info"
        raise NotImplementedError(msg)

    @override
    def update_title(self, title: Title, *, force: bool = False) -> None:
        preloaded_title = self._preload_title(
            title.key,
            source_key=title.source.key,
        ).one()
        self._update_and_upsert_title(preloaded_title, force=force)

    @override
    def update_season(self, season: Season) -> None:
        preloaded_season = self._preload_season(season.id, preload_title=True).one()
        self._update_and_upsert_title(preloaded_season.title)

    @override
    def update_episode(self, episode: Episode) -> None:
        preloaded_episode = self._preload_episode(episode.id, preload_source=True).one()
        self._update_and_upsert_title(preloaded_episode.season.title)

    def _update_and_upsert_title(
        self,
        title: Title,
        *,
        force: bool = False,
    ) -> None:
        """Update all files then upsert the title.

        Title files are updated using Title.update_at and the File.update_at values.
        Season files are updated using Season.update_at and the File.update_at values.
        Episode files are updated using Episode.update_at and the File.update_at values.
        """
        self._preload_and_download_files(title)
        self._upsert_title(title.source, title.key, force=force)

    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.parse_url(url)
        if title := self._preload_title(media_info.title_key).one_or_none():
            return self._import_results(title, media_info)

        self._preload_and_download_files(media_info.title_key)
        title = self._upsert_title(self.source, media_info.title_key)
        return self._import_results(title, media_info)

    def _import_results(
        self,
        title: Title,
        media_info: ParsedURL | None = None,
    ) -> list[URLImportResult]:
        """Return a list of import results for the given title and media info."""

        result_titles = [title, *title.canonical_titles]

        if media_info and media_info.episode_key is not None:
            episodes = [self._imported_episode(title, media_info.episode_key)]
            return [
                URLImportResult.episode_import_results(result_title, episodes)
                for result_title in result_titles
            ]

        if media_info and media_info.season_key is not None:
            seasons = [self._imported_season(title, media_info.season_key)]
            return [
                URLImportResult.season_import_results(result_title, seasons)
                for result_title in result_titles
            ]

        return [
            URLImportResult.title_import_results(result_title)
            for result_title in result_titles
        ]

    def _imported_season(self, title: Title, season_key: str) -> Season:
        """Return the season with the given key from the title."""
        for season in title.seasons:
            if season.key == season_key:
                return season

        msg = f"Season {season_key} not found in title {title.key}"
        raise ValueError(msg)

    def _imported_episode(self, title: Title, episode_key: str) -> Episode:
        """Return the episode with the given key from the title."""
        for season in title.seasons:
            for episode in season.episodes:
                if episode.key == episode_key:
                    return episode

        msg = f"Episode {episode_key} not found in title {title.key}"
        raise ValueError(msg)

    def on_update_failure(
        self,
        record: Title | Season | Episode,
        error: Exception,  # noqa: ARG002 - `error` is used by overrides.
    ) -> None:
        """Default implementation for when any update fails for any record."""
        # TODO: Should this still override AbstractPlugin's implementation?
        record.update_at = tz_datetime.max()
