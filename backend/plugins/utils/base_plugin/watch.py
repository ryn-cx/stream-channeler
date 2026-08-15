# TODO: Validate
import uuid
from abc import ABC
from datetime import datetime

from sqlmodel import Session, col, select

from app.canonical_media.filters import canonical_id_of
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.identifiers import watched_dates_by_canonical_id


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
    def _get_watched_dates_by_canonical_id(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[uuid.UUID, list[datetime]]:
        """Load watched dates grouped by the episode they are of.

        A watch is recorded against the one link that played it, so a date is
        looked up across every link to the same episode rather than under the
        link this import happens to be walking. A row that links to nothing is
        the episode itself rather than a row with no episode behind it, so it is
        its own group - which is the whole of a plugin nothing has been minted
        for.
        """
        return watched_dates_by_canonical_id(
            self.session,
            user.id,
            {canonical_id_of(episode) for episode in episodes_by_key.values()},
        )
