# TODO: Validate
"""Reading a stored title again, and saying when it should be read next."""

from __future__ import annotations

from abc import ABC
from datetime import datetime, timedelta

from loguru import logger

from app.episodes.models import Episode
from app.episodes.preload import preload_episodes
from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.base_plugin_v3.soft_delete import BaseSoftDeleteMixin


# TODO: Validate
class BaseUpdateMixin(BaseSoftDeleteMixin, ABC):
    # TODO: Validate
    def update_show(self, show: Show, *, force: bool = False) -> None:
        source_name = show.source.name or show.source.key
        show_name = f"{show.name} ({show.key})" if show.name else show.key
        logger.info("Updating show: {} - {}", source_name, show_name)
        stored_show = self._preload_show(show.key, source_key=show.source.key).one()
        self._update_and_upsert_show(stored_show, stored_show.update_at, force=force)

    # TODO: Validate
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        stored_season = self._preload_season(season.id, preload_show=True).one()
        self._update_and_upsert_show(stored_season.show, stored_season.update_at)

    # TODO: Validate
    def update_episode(self, episode: Episode) -> None:
        logger.info("Updating episode: {}", episode.key)
        stored_episode = self._preload_episode(episode.id, preload_source=True).one()
        self._update_and_upsert_show(
            stored_episode.season.show,
            stored_episode.update_at,
        )

    # TODO: Validate
    def _set_weekly_updates_from_episodes(
        self,
        show: Show,
        *,
        update_show: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the `Show`/`Season` based on `Episode.air_date`.

        `update_at` will be set to be a week after the latest `Episode.air_date` if
        that is a better `update_at` value than the current `update_at` value.
        """
        preload_episodes(self.session, [show])
        for season in show.active_children:
            for episode in season.active_children:
                if episode.air_date:
                    update_at = episode.air_date + timedelta(days=7)
                    if update_seasons:
                        season.set_update_at(update_at)
                    if update_show:
                        show.set_update_at(update_at)

    # TODO: Validate
    def _update_and_upsert_show(
        self,
        show: Show,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        """Read a stored listing again, and settle what its episodes are linked to.

        An update writes the same episodes an import does, so which TMDB episode
        each of them is is worked out here too. Only the matching, and not the
        rest of what an import settles: which title a listing is linked to is
        read off a website's own account of itself, which an update is not
        reading, and a canonical row has no title to point at at all.
        """
        self._preload_show(show.id, preload_episodes=True).one()
        self.upsert_show(show.source, show.key, update_at=update_at, force=force)
