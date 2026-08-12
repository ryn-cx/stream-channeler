# TODO: Validate
from abc import ABC
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, col, select

from app.canonical_episodes.models import CanonicalEpisode
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
    ) -> dict[str, list[datetime]]:
        """Load watched dates grouped by the key of the episode they are of."""
        canonical_ids = {
            episode.canonical_episode_id
            for episode in episodes_by_key.values()
            if episode.canonical_episode_id
        }
        if not canonical_ids:
            return {}
        canonical_keys = self.session.exec(
            select(CanonicalEpisode.key).where(
                col(CanonicalEpisode.id).in_(canonical_ids),
                col(CanonicalEpisode.key).is_not(None),
            ),
        ).all()
        if not canonical_keys:
            return {}
        statement = select(Watch.canonical_episode_key, Watch.watch_date).where(
            Watch.user_id == user.id,
            col(Watch.canonical_episode_key).in_(canonical_keys),
        )
        result: dict[str, list[datetime]] = defaultdict(list)
        for canonical_episode_key, watch_date in self.session.exec(statement):
            result[canonical_episode_key].append(watch_date)
        return result
