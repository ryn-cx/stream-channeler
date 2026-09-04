# TODO: Validate
"""Reading a stored series again off what TMDB says has changed."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.canonical_media.keys import tmdb_episode_key, tmdb_season_key
from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.upsert import SeriesUpsertMixin
from plugins.utils.base_plugin_v3.files import COMPLETED_STATUS

if TYPE_CHECKING:
    from app.shows.models import Show
    from plugins.TMDB.files import _TVSeasonsChanges, _TVSeriesChanges


# TODO: Validate
class SeriesUpdateMixin(SeriesUpsertMixin):
    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        # Individual files are updated based on what data has changed instead of
        # updating all of the files like most plugins.
        self._download_changes_file(show)
        self._import_all_show_changes(show)
        self._import_all_season_changes(show)
        self._preload_show(show.id, preload_episodes=True).one()
        self.upsert_show(show.source, show.key, force=force)

    # TODO: Validate
    def _download_changes_file(self, show: Show) -> None:
        if show.update_at and show.update_at <= tz_datetime.now():
            self.tv_series_changes_file(
                show.key, tz_datetime.now().date()
            ).download_if_outdated()

    # TODO: Validate
    def _import_all_show_changes(self, show: Show) -> None:
        for changes_file in self.incomplete_tv_series_changes_files(show.key):
            self._import_single_show_changes(show.key, changes_file)

    # TODO: Validate
    def _import_single_show_changes(
        self,
        show_key: str,
        changes_file: _TVSeriesChanges,
    ) -> None:
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)

        for change in changes_file.parsed().changes:
            for item in change.items:
                changed_at = tz_datetime.fromisoformat(
                    item.time.replace(" UTC", "+00:00"),
                )
                # The details file lists the seasons, so it is read again before the
                # seasons are, otherwise a season added since the last read is named
                # by a change and found in nothing.
                self.tv_series_details_file(tmdb_id).download_if_outdated(changed_at)
                # There are no episode specific files so they are grouped with the
                # seasons as they can be used to detect new episodes.
                if change.key in {"season", "episode"}:
                    season_keys: list[str]
                    # If the show uses altrernative episode ordering the only way to
                    # properly update it is to update all of the seasons.
                    if show_chosen_group_id(self.session, self.source, show_key):
                        season_keys = self._season_keys_from_show_files(show_key)
                    else:
                        # Ignore the errors because these should always have a value.
                        # The type error occurs because different keys have different
                        # data structures but this is not easily added to the model
                        # because the keys are just a string.
                        season_keys = [
                            tmdb_season_key(TMDBMediaType.tv, item.value.season_id),  # type: ignore[union-attr, arg-type]
                        ]
                    for season_key in season_keys:
                        self._download_if_outdated(
                            self._season_files(season_key, show_key),
                            changed_at,
                        )
                        self.tv_seasons_changes_file(
                            season_key,
                            changed_at.date(),
                        ).download_if_outdated()

        changes_file.database_record.status = COMPLETED_STATUS

    def _import_all_season_changes(self, show: Show) -> None:
        for season_key in self._season_keys_from_show_files(show.key):
            for changes_file in self.incomplete_tv_seasons_changes_files(season_key):
                self._import_single_season_changes(
                    season_key,
                    show.key,
                    changes_file,
                )

    def _import_single_season_changes(
        self,
        season_key: str,
        show_key: str,
        changes_file: _TVSeasonsChanges,
    ) -> None:
        for change in changes_file.parsed().changes:
            if change.key != "episode":
                continue
            for item in change.items:
                changed_at = tz_datetime.fromisoformat(
                    item.time.replace(" UTC", "+00:00"),
                )
                # The season file lists the episodes and the numbering the API asks
                # for them by, so it is read again before the episode's files are
                # named, otherwise an episode added since the last read is named by
                # a change and numbered off nothing.
                self._download_if_outdated(
                    self._season_files(season_key, show_key),
                    changed_at,
                )
                # Ignore the errors because these should always have a value. The
                # type error occurs because different keys have different data
                # structures but this is not easily added to the model because the
                # keys are just a string.
                episode_key = tmdb_episode_key(TMDBMediaType.tv, item.value.episode_id)  # type: ignore[union-attr, arg-type]
                self._download_if_outdated(
                    self._episode_files(episode_key, season_key, show_key),
                    changed_at,
                )

        changes_file.database_record.status = COMPLETED_STATUS
