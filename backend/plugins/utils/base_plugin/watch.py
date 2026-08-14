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

        A watch is of the episode itself rather than of one website's copy, so
        recording a single watch per key is enough - no per-source duplication is
        needed.
        """
        if not episode_keys:
            return {}
        statement = (
            select(Episode)
            .join(Season, col(Episode.season_id) == col(Season.id))
            .join(Show, col(Season.show_id) == col(Show.id))
            .join(Source)
            .where(Source.plugin_id == self.plugin.id)
            .where(col(Episode.key).in_(episode_keys))
        )
        return {episode.key: episode for episode in self.session.exec(statement)}

    # TODO: Validate
    def _get_watched_dates_by_identifier(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[str, list[datetime]]:
        """Load watched dates grouped by the identifier of the episode they are of.

        A row that links to nothing is the episode itself rather than a row with
        no episode behind it, so its own identifier is what a watch of it holds.
        A plugin nothing has been minted for has only such rows, and reading the
        link alone would leave every one of its watches unaccounted for.
        """
        watch_identifiers = {
            (episode.canonical_episode or episode).watch_identifier
            for episode in episodes_by_key.values()
        }
        if not watch_identifiers:
            return {}
        statement = select(Watch.watch_identifier, Watch.watch_date).where(
            Watch.user_id == user.id,
            col(Watch.watch_identifier).in_(watch_identifiers),
        )
        result: dict[str, list[datetime]] = defaultdict(list)
        for watch_identifier, watch_date in self.session.exec(statement):
            result[watch_identifier].append(watch_date)
        return result
