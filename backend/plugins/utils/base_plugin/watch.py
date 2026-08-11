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


# TODO: Validate
class WatchMixin(ABC):
    session: Session
    plugin: Plugin

    # TODO: Validate
    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load this plugin's `Episode` for each key.

        A watch keys on the episode's `episode_identifier`, which is shared across
        every source for the same content, so recording a single watch per key is
        enough - no per-source duplication is needed.
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
    def _get_watched_identifier_dates(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[str, list[datetime]]:
        """Load watched dates grouped by `episode_identifier`."""
        identifiers = {
            episode.episode_identifier for episode in episodes_by_key.values()
        }
        if not identifiers:
            return {}
        statement = select(Watch.episode_identifier, Watch.watch_date).where(
            Watch.user_id == user.id,
            col(Watch.episode_identifier).in_(identifiers),
        )
        result: dict[str, list[datetime]] = defaultdict(list)
        for episode_identifier, watch_date in self.session.exec(statement):
            result[episode_identifier].append(watch_date)
        return result
