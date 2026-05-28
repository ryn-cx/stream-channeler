# TODO: Validate
from abc import ABC
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.models import Watch


class WatchMixin(ABC):
    session: Session
    plugin: Plugin

    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load episodes by their keys, scoped to this plugin."""
        if not episode_keys:
            return {}
        statement = (
            select(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .where(Source.plugin_id == self.plugin.id)
            .where(col(Episode.key).in_(episode_keys))
        )
        return {episode.key: episode for episode in self.session.exec(statement)}

    def _get_watched_episode_dates(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[str, list[datetime]]:
        """Load watched dates grouped by episode ID."""
        if not episodes_by_key:
            return {}
        statement = select(Watch.episode_id, Watch.watch_date).where(
            Watch.user_id == user.id,
            col(Watch.episode_id).in_(
                [episode.id for episode in episodes_by_key.values()],
            ),
        )
        result: dict[str, list[datetime]] = defaultdict(list)
        for episode_id, watch_date in self.session.exec(statement):
            result[str(episode_id)].append(watch_date)
        return result
