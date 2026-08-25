# TODO: Validate
"""Which of a title's records TMDB has edited since they were last read.

A title is read again on a timer, and reading one in full is a file per season
whether anything moved or not. What TMDB's changes endpoints answer is which
records moved, so a read starts by asking that and goes no further than the
records named.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from tminidb.changes.tv_series.models import Item

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.TMDB.files import ShowChanges, change_datetime
from plugins.TMDB.import_url import ImportURLMixin
from plugins.TMDB.keys import parse_show_key, season_key
from plugins.utils.base_plugin.files import COMPLETED_STATUS, EXTRA_STATUS_FIELD

if TYPE_CHECKING:
    from datetime import datetime

    from app.shows.models import Show

SHOW_DETAIL_CHANGE_KEYS = frozenset(
    {
        "adult",
        "also_known_as",
        "alternative_titles",
        "biography",
        "birthday",
        "budget",
        "cast",
        "certifications",
        "character_names",
        "created_by",
        "crew",
        "deathday",
        "episode_run_time",
        "freebase_id",
        "freebase_mid",
        "general",
        "genres",
        "homepage",
        "images",
        "imdb_id",
        "languages",
        "name",
        "network",
        "origin_country",
        "original_name",
        "original_title",
        "overview",
        "parts",
        "place_of_birth",
        "plot_keywords",
        "production_companies",
        "production_countries",
        "releases",
        "revenue",
        "season_regular",
        "spoken_languages",
        "status",
        "tagline",
        "title",
        "translations",
        "tvdb_id",
        "tvrage_id",
        "type",
        "videos",
    },
)

SEASON_DETAIL_CHANGE_KEYS = frozenset(
    {
        "air_date",
        "cast",
        "crew",
        "episode",
        "episode_number",
        "general",
        "guest_stars",
        "images",
        "name",
        "overview",
        "production_code",
        "runtime",
        "season",
        "season_number",
        "season_regular",
        "translations",
        "video",
    },
)

EPISODE_TRANSLATIONS_CHANGE_KEYS = frozenset(
    {
        "translations",
    },
)

SUPPORTED_CHANGE_KEYS = (
    SHOW_DETAIL_CHANGE_KEYS
    | SEASON_DETAIL_CHANGE_KEYS
    | EPISODE_TRANSLATIONS_CHANGE_KEYS
)


# TODO: Validate
class UpdateMixin(ImportURLMixin, register=False):
    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._set_current_show(show.key)
        media_type, _ = parse_show_key(show.key)
        if media_type == MediaType.movie:
            # Movie ignores changes because there is only a single file so i is more
            # efficient to directly update it instead of checking for changes.
            super().update_show(show, force=force)
        else:
            self._download_and_import_changed_title_files(show.key)
            self._preload_show(show.id, preload_episodes=True).one()
            self.upsert_show(show.source, show.key, force=force)
        self._import_listed_sources(show.key, show)

    # TODO: Validate
    def _download_and_import_changed_title_files(
        self,
        show_key: str,
    ) -> None:
        self.show_changes_file(
            show_key,
            tz_datetime.now().date(),
        ).download_if_outdated()

        _cache = self._preload_show_files(show_key)
        for changes_file in self.incomplete_show_changes_files(show_key):
            self._import_show_changes(show_key, changes_file)
            changes_file.database_record.extra = {EXTRA_STATUS_FIELD: COMPLETED_STATUS}

        for key in self._season_keys_from_file(show_key):
            self._download_outdated_files(self._season_files(key, show_key))

    # TODO: Validate
    def _import_show_changes(self, show_key: str, changes_file: ShowChanges) -> None:
        """Import show changes by updating files that are no longer up to date."""
        _, tmdb_id = parse_show_key(show_key)
        translations_files = self.stored_episode_translations_files(tmdb_id)

        for change in changes_file.changes():
            for item in change.items:
                changed_at = change_datetime(item.time)
                if change.key in SHOW_DETAIL_CHANGE_KEYS:
                    self._update_changed_show_files(tmdb_id, changed_at)
                if change.key in SEASON_DETAIL_CHANGE_KEYS:
                    self._update_changed_season_files(show_key, item, changed_at)
                if change.key in EPISODE_TRANSLATIONS_CHANGE_KEYS:
                    self._download_outdated_files(translations_files, changed_at)
                if change.key not in SUPPORTED_CHANGE_KEYS:
                    message = f"{show_key} has an unknown change key: {change.key}"
                    raise ValueError(message)

    # TODO: Validate
    def _update_changed_show_files(self, tmdb_id: int, changed_at: datetime) -> None:
        self.show_detail_file(tmdb_id).download_if_outdated(changed_at)

    # TODO: Validate
    def _update_changed_season_files(
        self,
        show_key: str,
        item: Item,
        changed_at: datetime,
    ) -> None:
        stored_keys = self._season_keys_from_file(show_key)
        # What a change carries is whatever JSON TMDB wrote for that key, which
        # for a season is an object naming the season and for everything else is
        # a string or a number that names no season at all.
        changed = item.value
        named = (
            None
            if self._chosen_group_id(show_key) is not None
            else getattr(changed, "season_id", None)
        )
        key = None if named is None else season_key(MediaType.tv, named)
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
