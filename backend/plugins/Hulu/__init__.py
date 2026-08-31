# TODO: Validate
"""Hulu plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Hulu.base import HuluBase
from plugins.Hulu.channels import HuluChannels
from plugins.Hulu.handlers import (
    HuluImportURL,
    HulueEpisodeUpdater,
    HuluSeasonUpdater,
    HuluShowUpdater,
)
from plugins.utils.base_plugin_v2.facade import FacadePlugin

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class Hulu(FacadePlugin, HuluBase, register=True):
    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        return HuluImportURL.url_regex()

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        return HuluImportURL(self, url).import_url(canonical_show, force=force)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        HuluShowUpdater(self, show).update_show(force=force)

    # TODO: Validate
    @override
    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        HuluShowUpdater(self, show).on_failure(error)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        HuluSeasonUpdater(self, season).update_season()

    # TODO: Validate
    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        HuluSeasonUpdater(self, season).on_failure(error)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        HulueEpisodeUpdater(self, episode).update_episode()

    # TODO: Validate
    @override
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        HulueEpisodeUpdater(self, episode).on_failure(error)

    # TODO: Validate
    def initialize_channel(self, genre_ids: Collection[str] | None = None) -> None:
        HuluChannels(self).run(genre_ids)
