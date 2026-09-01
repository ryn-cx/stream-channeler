# TODO: Validate
"""Reading a title in, whether a URL named it or an id did.

A title is read again on a timer, and reading one in full is a file per season
whether anything moved or not. What TMDB's changes endpoints answer is which
records moved, so a read starts by asking that and goes no further than the
records named.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from tminidb.tv_series.changes.models import Item

from app.canonical_media.keys import (
    tmdb_season_key,
    tmdb_show_key,
)
from app.media.media_type import MediaType
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.base import TMDBBase
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.files import ShowChanges
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.utils import change_datetime
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v2.files import (
    COMPLETED_STATUS,
    EXTRA_STATUS_FIELD,
    BaseFile,
)
from plugins.utils.base_plugin_v2.importer import Importer

if TYPE_CHECKING:
    from datetime import datetime

    from app.seasons.models import Season

# from plugins.WatchMode import WatchMode  # noqa: ERA001


# TODO: Validate
def _title_url_regex(media_type: MediaType) -> str:
    return rf"\/{media_type}\/(?P<{media_type}_tmdb_id>\d+)"


# TODO: Validate
class TMDBImporter(Importer, TMDBBase):
    _MOVIE_URL_REGEX = _title_url_regex(MediaType.movie)
    _TV_URL_REGEX = _title_url_regex(MediaType.tv)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._TV_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        for media_type, url_regex in (
            (MediaType.movie, self._MOVIE_URL_REGEX),
            (MediaType.tv, self._TV_URL_REGEX),
        ):
            if match := re.match(domain_regex + url_regex, url):
                tmdb_id = int(match.group(f"{media_type}_tmdb_id"))
                self.raise_if_invalid_file(
                    self.title_page_file(media_type, tmdb_id),
                    url,
                )
                detail_file: BaseFile[Any]
                if media_type == MediaType.movie:
                    detail_file = self.movie_detail_file(tmdb_id)
                else:
                    detail_file = self.show_detail_file(tmdb_id)
                self.raise_if_invalid_file(detail_file, url)
                return tmdb_show_key(media_type, tmdb_id)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        # TMDB should always be canonical so if it is imported with a caonical_show
        # something has gone wrong.
        if canonical_show is not None:
            msg = "canonical_show should be None when importing TMDB URLs."
            raise InvalidURLError(msg)

        show_key = self._parse_url(url)
        existing_show = self._preload_show(
            show_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_show:
            _cache = self._download_show_files_and_children(show_key)
            existing_show = self.upsert_show(self.source, show_key)
            self._import_media_from_other_websites(show_key, existing_show)

        return self._import_results(existing_show)

    # TODO: Validate
    @override
    def _update_show(self, show: Show, *, force: bool = False) -> None:
        media_type, _ = get_media_type_and_tmdb_id(show.key)
        if media_type == MediaType.movie:
            # For movies it is more efficient to update it directly since it only has 2
            # files that are listed on the changes endpoint (watch provider changes are
            # not listed on the changes endpoint).
            super()._update_show(show, force=force)
        else:
            self._download_and_import_changed_title_files(show)
            self._preload_show(show.id, preload_episodes=True).one()
            self.upsert_show(show.source, show.key, force=force)
        self.sync_show_watch_providers(show.key)
        self._import_media_from_other_websites(show.key, show)

    # TODO: Validate
    @override
    def _update_season(self, season: Season) -> None:
        super()._update_season(season)
        self.sync_season_key_watch_providers(season.key, season.show.key)

    # TODO: Validate
    def _download_and_import_changed_title_files(self, show: Show) -> None:
        if show.update_at is not None:
            self.show_changes_file(
                show.key,
                tz_datetime.now().date(),
            ).download_if_outdated()

        _cache = self._preload_show_files(show.key)
        for changes_file in self.incomplete_show_changes_files(show.key):
            self._import_show_changes(show.key, changes_file)
            changes_file.database_record.extra = {EXTRA_STATUS_FIELD: COMPLETED_STATUS}

        for key in self._season_keys_from_show_files(show.key):
            self._download_outdated_files(self._season_files(key, show.key))

    # TODO: Validate
    def _import_show_changes(self, show_key: str, changes_file: ShowChanges) -> None:
        """Import show changes by updating files that are no longer up to date."""
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        translations_files = self.stored_episode_translations_files(tmdb_id)

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
        self.show_detail_file(tmdb_id).download_if_outdated(changed_at)

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
        key = None if named is None else tmdb_season_key(MediaType.tv, named)
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
