# TODO: Validate
import uuid
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


# TODO: Validate
class WatchMixin(ABC):
    session: Session
    plugin: Plugin

    # TODO: Validate
    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load this plugin's `Episode` for each key.

        A watch is of the episode itself rather than of one website's copy, so
        recording a single watch per key is enough - no per-source duplication is
        needed.
        """
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

    # TODO: Validate
    def _get_watched_canonical_dates(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[uuid.UUID, list[datetime]]:
        """Load watched dates grouped by the canonical episode they are of."""
        canonical_ids = {
            episode.canonical_episode_id
            for episode in episodes_by_key.values()
            if episode.canonical_episode_id
        }
        if not canonical_ids:
            return {}
        statement = select(Watch.canonical_episode_id, Watch.watch_date).where(
            Watch.user_id == user.id,
            col(Watch.canonical_episode_id).in_(canonical_ids),
        )
        result: dict[uuid.UUID, list[datetime]] = defaultdict(list)
        for canonical_episode_id, watch_date in self.session.exec(statement):
            result[canonical_episode_id].append(watch_date)
        return result
