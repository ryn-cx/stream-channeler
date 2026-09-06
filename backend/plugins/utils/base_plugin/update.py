# TODO: Validate
"""Reading a stored title again, and saying when it should be read next."""

from __future__ import annotations

from abc import ABC
from collections.abc import Iterable
from datetime import datetime, timedelta

from app.episodes.preload import preload_episodes
from app.seasons.models import Season
from app.titles.models import Title
from app.utils.update_at import staggered_monthly_update_at
from plugins.utils.base_plugin.soft_delete import BaseSoftDeleteMixin


# TODO: Validate
class BaseUpdateMixin(BaseSoftDeleteMixin, ABC):
    # TODO: Validate
    def _mark_mismatched_titles_as_outdated(
        self,
        listed_title_keys: Iterable[str],
        source_key: str | None = None,
    ) -> None:
        """Mark mismatched titles as outdated.

        There are two ways a title can be considered mismatched:
        1. It is listed in `listed_title_keys` but has been deleted.
        2. It is not listed in `listed_title_keys` but exists and is not deleted.

        Args:
            listed_title_keys: All of the title keys that are expected to exist for the source.
            source_key: The key of the source to check for mismatched titles. If None, all sources are checked.
        """
        listed = set(listed_title_keys)
        data_timestamp = self.source_data_timestamp()
        for source in self._preload_sources(source_key, preload_titles=True):
            for title in source.titles:
                is_listed = title.key in listed
                is_deleted = title.deleted_at is not None
                if is_listed == is_deleted:
                    title.set_update_at(data_timestamp)

    # TODO: Validate
    def _set_weekly_updates_from_episodes(
        self,
        title: Title,
        *,
        update_title: bool = True,
        update_seasons: bool = True,
    ) -> None:
        """Set update_at on the `Title`/`Season` based on `Episode.air_date`.

        `update_at` will be set to be a week after the latest `Episode.air_date` if
        that is a better `update_at` value than the current `update_at` value.
        """
        preload_episodes(self.session, [title])
        for season in title.active_children:
            for episode in season.active_children:
                if episode.air_date:
                    update_at = episode.air_date + timedelta(days=7)
                    if update_seasons:
                        season.set_update_at(update_at)
                    if update_title:
                        title.set_update_at(update_at)

    # TODO: Validate
    def _set_season_update_at_based_on_last_episode(self, season: Season) -> None:
        if not season.data_timestamp:  # Should be impossible
            msg = f"Record {season.key} has no data_timestamp"
            raise ValueError(msg)

        preload_episodes(self.session, [season.title])
        for episode in season.active_children:
            if episode.air_date:
                season.set_update_at(episode.air_date)
                season.set_update_at(episode.air_date + timedelta(days=7))

        season.set_update_at(
            staggered_monthly_update_at(season.key, season.data_timestamp),
        )

    # TODO: Validate
    def _update_and_upsert_title(
        self,
        title: Title,
        update_at: datetime | None = None,
        *,
        force: bool = False,
    ) -> None:
        """Update all files then upsert the title.

        Title files are updated using Title.udpate and the File.update_at values.
        Season files are updated using Season.update and the File.update_at values.
        Episode files are updated using Episode.update and the File.update_at values.
        """
        self._download_title_files_and_children(title.key, update_at)
        self._preload_title(title.id, preload_episodes=True).one()
        self.upsert_title(title.source, title.key, force=force)
