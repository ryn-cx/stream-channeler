# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

from loguru import logger

from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.core import PluginCore, ReadURLCore

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class PluginWorker(PluginCore, ABC, register=False):
    # TODO: Validate
    def __init__(self, owner: PluginCore) -> None:
        super().__init__(owner.session)
        self._file_cache = owner._file_cache  # noqa: SLF001


# TODO: Validate
class URLImporter(PluginWorker, ReadURLCore, ABC, register=False):
    url: str

    # TODO: Validate
    def __init__(self, owner: PluginCore, url: str) -> None:
        super().__init__(owner)
        self.url = url
        self._parse_url(url)

    # TODO: Validate
    def import_url(
        self,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = self._show_key
        if not force and (show := self._preload_show(show_key).one_or_none()):
            return self._import_results(show)

        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
            if not force and (show := self._preload_show(show_key).one_or_none()):
                return self._import_results(show)

        show = self.upsert_show(
            self._url_source(),
            show_key,
            canonical_show=canonical_show,
            force=force,
        )
        return self._import_results(show)


# TODO: Validate
class ShowUpdater(PluginWorker, ABC, register=False):
    show: Show

    # TODO: Validate
    def __init__(self, owner: PluginCore, show: Show) -> None:
        super().__init__(owner)
        self.show = show

    # TODO: Validate
    def update_show(self, *, force: bool = False) -> None:
        source_name = self.show.source.name or self.show.source.key
        show_name: str
        if self.show.name:
            show_name = f"{self.show.name} ({self.show.key})"
        else:
            show_name = self.show.key
        logger.info("Updating show: {} - {}", source_name, show_name)
        show = self._preload_show(self.show.key, source_key=self.show.source.key).one()
        self._update_and_upsert_show(show, show.update_at, force=force)

    # TODO: Validate
    def on_failure(self, error: Exception) -> None:  # noqa: ARG002 - `error` is used by overrides.
        self.show.update_at = tz_datetime.max()


# TODO: Validate
class SeasonUpdater(PluginWorker, ABC, register=False):
    season: Season

    # TODO: Validate
    def __init__(self, owner: PluginCore, season: Season) -> None:
        super().__init__(owner)
        self.season = season

    # TODO: Validate
    def update_season(self) -> None:
        logger.info("Updating season: {}", self.season.key)
        season = self._preload_season(self.season.id, preload_show=True).one()
        self._download_season_files_and_children(season, update_at=season.update_at)
        self._update_and_upsert_show(season.show)

    # TODO: Validate
    def on_failure(self, error: Exception) -> None:  # noqa: ARG002 - `error` is used by overrides.
        self.season.update_at = tz_datetime.max()


# TODO: Validate
class EpisodeUpdater(PluginWorker, ABC, register=False):
    episode: Episode

    # TODO: Validate
    def __init__(self, owner: PluginCore, episode: Episode) -> None:
        super().__init__(owner)
        self.episode = episode

    # TODO: Validate
    def update_episode(self) -> None:
        logger.info("Updating episode: {}", self.episode.key)
        episode = self._preload_episode(self.episode.id, preload_source=True).one()
        self._download_episode_files(episode, update_at=episode.update_at)
        self._update_and_upsert_show(episode.season.show)

    # TODO: Validate
    def on_failure(self, error: Exception) -> None:  # noqa: ARG002 - `error` is used by overrides.
        self.episode.update_at = tz_datetime.max()
