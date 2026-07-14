# TODO: Validate
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.base_plugin.download import DownloadMixin


@dataclass
class UpToDate[RecordT]:
    """An up-to-date media record: its existing entity and data timestamp.

    Falsy so that ``if check:`` narrows to the outdated variant.
    """

    record: RecordT
    data_timestamp: datetime

    def __bool__(self) -> Literal[False]:
        """Report an up-to-date record as falsy."""
        return False


@dataclass
class Outdated[RecordT]:
    """A new or outdated media record: its existing entity (or None) and timestamp.

    Truthy so that ``if check:`` narrows to this variant.
    """

    record: RecordT | None
    data_timestamp: datetime

    def __bool__(self) -> Literal[True]:
        """Report a new or outdated record as truthy."""
        return True


type CheckResult[RecordT] = UpToDate[RecordT] | Outdated[RecordT]


class CheckMixin(DownloadMixin):
    def _show_chek(
        self,
        source: Source,
        show_key: str,
    ) -> CheckResult[Show]:
        """Return the show's existing entity, its data timestamp, and staleness."""
        existing_show = Show.get_from_memory(self.session, source, show_key)
        show_timestamp = self.show_data_timestamp(show_key)
        if (
            existing_show
            and existing_show.data_timestamp == show_timestamp
            and not existing_show.deleted_at
        ):
            return UpToDate(record=existing_show, data_timestamp=show_timestamp)
        return Outdated(record=existing_show, data_timestamp=show_timestamp)

    def _season_check(
        self,
        show: Show,
        season_key: str,
        show_key: str,
    ) -> CheckResult[Season]:
        """Return the season's existing entity, its data timestamp, and staleness."""
        existing_season = Season.get_from_memory(self.session, show, season_key)
        season_timestamp = self.season_data_timestamp(season_key, show_key)
        if (
            existing_season
            and existing_season.data_timestamp == season_timestamp
            and not existing_season.deleted_at
        ):
            return UpToDate(record=existing_season, data_timestamp=season_timestamp)
        return Outdated(record=existing_season, data_timestamp=season_timestamp)

    def _episode_check(
        self,
        episode_key: str,
        season: Season,
        show_key: str,
    ) -> CheckResult[Episode]:
        """Return the episode's existing entity, its data timestamp, and staleness."""
        existing_episode = Episode.get_from_memory(self.session, season, episode_key)
        episode_timestamp = self.episode_data_timestamp(
            episode_key,
            season.key,
            show_key,
        )
        if (
            existing_episode
            and existing_episode.data_timestamp == episode_timestamp
            and not existing_episode.deleted_at
        ):
            return UpToDate(record=existing_episode, data_timestamp=episode_timestamp)
        return Outdated(record=existing_episode, data_timestamp=episode_timestamp)
