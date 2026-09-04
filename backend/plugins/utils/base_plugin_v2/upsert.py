# TODO: Validate
"""Writing what a website says about a title into the rows that stand for it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.episodes.models import Episode
from app.models import BaseMediaMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.core import BasePluginCore
from plugins.utils.base_plugin_v2.outdated_check import BaseOutdatedCheckMixin


# TODO: Validate
class BaseUpsertMixin(BasePluginCore, BaseOutdatedCheckMixin, ABC):
    # TODO: Validate
    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    # TODO: Validate
    def _upsert_show_object(
        self,
        show: Show,
        source: Source,
        existing_show: Show | None,
        show_key: str,
    ) -> Show:
        """A show built fresh off the source's files knows nothing of the canonical
        shows the stored one is linked to. Those are rows of `ShowCanonicalShow`
        rather than columns here, so there is nothing to write away and nothing to
        carry over: which canonical show it is linked to is settled once its
        episodes are written, which is where `upsert_show` ends.
        """
        return show.upsert_and_set_update_at(source, existing_show)

    # TODO: Validate
    def _upsert_season_object(
        self,
        season: Season,
        show: Show,
        existing_season: Season | None,
        show_key: str,
    ) -> Season:
        return season.upsert_and_set_update_at(show, existing_season)

    # TODO: Validate
    def _upsert_episode_object(
        self,
        episode: Episode,
        season: Season,
        existing_episode: Episode | None,
        show_key: str,
    ) -> Episode:
        """The links the stored record carries are rows of their own and stay where
        they are, so nothing here has to carry them over. The note travels with
        them: how a link came to be made is most of what says whether it should
        be kept, so an episode that keeps its links keeps the reason for them
        too.
        """
        if existing_episode:
            episode.canonical_episode_note = existing_episode.canonical_episode_note
        return episode.upsert_and_set_update_at(season, existing_episode)

    # TODO: Validate
    @abstractmethod
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        """Store the listing `show_key` names, and settle what it stands for.

        Every plugin ends this by handing what it wrote to `settle_show`, which is
        what settles the title the listing is linked to. Done there rather than
        by whatever called, because it is part of writing a listing, and done at
        the end rather than as the row is written, since the episodes read
        against the title are the ones the write has just put there.

        `canonical_show` is the title a caller already knows the listing to be,
        which is what an import handing a title from one plugin to another knows
        and nothing else does.
        """

    # TODO: Validate
    def upsert_source(self, source_key: str) -> Source:
        """Create or update the plugin's `Source` record(s)."""
        source = Source.get_from_memory(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)
