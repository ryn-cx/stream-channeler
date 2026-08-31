# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from app.utils import tz_datetime
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin_v2.core import ReadURLCore
from plugins.utils.base_plugin_v2.facade import FacadePlugin

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.plugins.models import Plugin
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class BasePlugin(FacadePlugin, ABC, register=False):
    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._update_show(show, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        self._update_season(season)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._update_episode(episode)

    # TODO: Validate
    @override
    def on_update_plugin_failure(self, plugin: Plugin, error: Exception) -> None:
        plugin.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_source_failure(self, source: Source, error: Exception) -> None:
        source.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        show.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.max()

    # TODO: Validate
    @override
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        episode.update_at = tz_datetime.max()


# TODO: Validate
class ReadURLPlugin(ReadURLCore, BasePlugin, ABC, register=False):
    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        self._parse_url(url)
        return self._import_read_url(canonical_show, force=force)
