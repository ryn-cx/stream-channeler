# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Pluto.upsert import UpsertMixin

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class UpdateMixin(UpsertMixin):
    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._set_media_type_from_show(show)
        super().update_show(show, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        self._set_media_type_from_show(season.show)
        super().update_season(season)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._set_media_type_from_show(episode.season.show)
        super().update_episode(episode)
