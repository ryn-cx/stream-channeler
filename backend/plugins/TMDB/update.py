# TODO: Validate
"""Reading a stored series again off what TMDB says has changed."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.canonical_media.keys import tmdb_season_key
from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.upsert import SeriesUpsertMixin
from plugins.TMDB.utils import change_datetime
from plugins.utils.base_plugin_v2.files import COMPLETED_STATUS

if TYPE_CHECKING:
    from datetime import datetime

    from tminidb.tv_series.changes.models import Item

    from app.shows.models import Show
    from plugins.TMDB.files import _TVSeriesChanges


# TODO: Validate
class SeriesUpdateMixin(SeriesUpsertMixin):
    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        # Individual files are updated based on what data has changed instead of
        # updating all of the files like most plugins.
        self._download_and_import_changed_title_files(show)
        self._preload_show(show.id, preload_episodes=True).one()
        self.upsert_show(show.source, show.key, force=force)

    # TODO: Validate
    def _download_and_import_changed_title_files(self, show: Show) -> None:
        if show.update_at:
            self.tv_series_changes_file(
                show.key,
                tz_datetime.now().date(),
            ).download_if_outdated()

        _cache = self._preload_show_files(show.key)
        for changes_file in self.incomplete_tv_series_changes_files(show.key):
            self._import_show_changes(show.key, changes_file)
            changes_file.database_record.status = COMPLETED_STATUS

        for key in self._season_keys_from_show_files(show.key):
            self._download_outdated_files(self._season_files(key, show.key))

    # TODO: Validate
    def _import_show_changes(
        self,
        show_key: str,
        changes_file: _TVSeriesChanges,
    ) -> None:
        """Import show changes by updating files that are no longer up to date."""
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        translations_files = self.tv_episodes_translations_files(tmdb_id)

        for change in changes_file.parsed().changes:
            for item in change.items:
                changed_at = change_datetime(item.time)
                if change.key in {"season", "episode"}:
                    self._update_changed_season_files(show_key, item, changed_at)
                else:
                    self._update_changed_show_files(tmdb_id, changed_at)
                if change.key == "translations":
                    self._download_outdated_files(translations_files, changed_at)

    # TODO: Validate
    def _update_changed_show_files(self, tmdb_id: int, changed_at: datetime) -> None:
        self.tv_series_details_file(tmdb_id).download_if_outdated(changed_at)

    # TODO: Validate
    def _update_changed_season_files(
        self,
        show_key: str,
        item: Item,
        changed_at: datetime,
    ) -> None:
        stored_keys = self._season_keys_from_show_files(show_key)
        # What a change carries is whatever JSON TMDB wrote for that key, which
        # for a season is an object naming the season and for everything else is
        # a string or a number that names no season at all.
        changed = item.value
        named = (
            None
            if show_chosen_group_id(self.session, self.source, show_key) is not None
            else getattr(changed, "season_id", None)
        )
        key = None if named is None else tmdb_season_key(TMDBMediaType.tv, named)
        changed_keys: list[str]
        if key is None:
            changed_keys = stored_keys
        elif key in stored_keys:
            changed_keys = [key]
        else:
            changed_keys = []
        for changed_key in changed_keys:
            self._download_outdated_files(
                self._season_files(changed_key, show_key),
                changed_at,
            )
