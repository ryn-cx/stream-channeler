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

    def _get_episodes_by_key(self, episode_keys: list[str]) -> dict[str, list[Episode]]:
        """Load the episodes each key should record a watch against.

        A key resolves to its episode in this plugin plus every episode in any
        plugin that shares a non-null `tmdb_id` with it, so an imported watch is
        recorded for the same episode across every source.
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
        plugin_episodes = {
            episode.key: episode for episode in self.session.exec(statement)
        }

        tmdb_ids = {
            episode.tmdb_id
            for episode in plugin_episodes.values()
            if episode.tmdb_id is not None
        }
        episodes_by_tmdb_id: dict[int, list[Episode]] = defaultdict(list)
        if tmdb_ids:
            tmdb_statement = select(Episode).where(col(Episode.tmdb_id).in_(tmdb_ids))
            for episode in self.session.exec(tmdb_statement):
                if episode.tmdb_id is not None:
                    episodes_by_tmdb_id[episode.tmdb_id].append(episode)

        result: dict[str, list[Episode]] = {}
        for key, episode in plugin_episodes.items():
            if episode.tmdb_id is None:
                result[key] = [episode]
                continue
            matches = {
                match.id: match for match in episodes_by_tmdb_id[episode.tmdb_id]
            }
            matches.setdefault(episode.id, episode)
            result[key] = list(matches.values())
        return result

    def _get_watched_episode_dates(
        self,
        user: User,
        episodes_by_key: dict[str, list[Episode]],
    ) -> dict[str, list[datetime]]:
        """Load watched dates grouped by episode ID."""
        episode_ids = {
            episode.id for episodes in episodes_by_key.values() for episode in episodes
        }
        if not episode_ids:
            return {}
        statement = select(Watch.episode_id, Watch.watch_date).where(
            Watch.user_id == user.id,
            col(Watch.episode_id).in_(episode_ids),
        )
        result: dict[str, list[datetime]] = defaultdict(list)
        for episode_id, watch_date in self.session.exec(statement):
            result[str(episode_id)].append(watch_date)
        return result
