# TODO: Validate
from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.media_info import plugin_for_tmdb_name, streaming_providers
from plugins.TMDB.upsert import UpsertMixin
from plugins.utils.base_plugin_v2.files import (
    COMPLETED_STATUS,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from plugins.TMDB.files import ProvidersFile


# TODO: Validate
class WatchProviderSyncMixin(UpsertMixin):
    # TODO: Validate
    def sync_show_watch_providers(self, show_key: str) -> None:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        files: Sequence[ProvidersFile]
        if media_type == MediaType.movie:
            self._download_watch_providers_file(
                self.movie_watch_providers_file(tmdb_id),
            )
            files = self.incomplete_movie_watch_providers_files(tmdb_id)
        else:
            self._download_watch_providers_file(self.tv_watch_providers_file(tmdb_id))
            files = self.incomplete_tv_watch_providers_files(tmdb_id)
        self._compare_watch_providers_files(show_key, files)

    # TODO: Validate
    def sync_season_watch_providers(self, show_key: str, season_number: int) -> None:
        media_type, tmdb_id = get_media_type_and_tmdb_id(show_key)
        if media_type != MediaType.tv:
            return
        self._download_watch_providers_file(
            self.season_watch_providers_file(tmdb_id, season_number),
        )
        self._compare_watch_providers_files(
            show_key,
            self.incomplete_season_watch_providers_files(tmdb_id, season_number),
        )

    # TODO: Validate
    def sync_season_key_watch_providers(self, season_key: str, show_key: str) -> None:
        for season_number in self.native_season_numbers(season_key, show_key):
            self.sync_season_watch_providers(show_key, season_number)

    # TODO: Validate
    @staticmethod
    def _download_watch_providers_file(file: ProvidersFile) -> None:
        file.download_if_outdated()
        record = file.database_record
        if record.content is None or record.status is not None:
            return
        record.status = "Incomplete"

    # TODO: Validate
    def _compare_watch_providers_files(
        self,
        show_key: str,
        files: Sequence[ProvidersFile],
    ) -> None:
        for older, newer in pairwise(files):
            self._mark_changed_providers(show_key, older, newer)
            record = older.database_record
            record.status = COMPLETED_STATUS
            record.update_at = None

    # TODO: Validate
    def _mark_changed_providers(
        self,
        show_key: str,
        older: ProvidersFile,
        newer: ProvidersFile,
    ) -> None:
        changed = _provider_names(older) ^ _provider_names(newer)
        if not changed:
            return
        self._mark_provider_records(show_key, changed, newer.data_timestamp)

    # TODO: Validate
    def _mark_provider_records(
        self,
        show_key: str,
        provider_names: set[str],
        update_at: datetime,
    ) -> None:
        plugin_keys = {
            plugin_class.plugin_name()
            for provider_name in provider_names
            if (plugin_class := plugin_for_tmdb_name(provider_name)) is not None
        }
        if not plugin_keys:
            return

        canonical_show = Show.get(self.session, self.source, show_key)
        if canonical_show is None:
            return

        for link in canonical_show.non_canonical_shows:
            listing = link.show
            if listing.source.plugin.key not in plugin_keys:
                continue
            listing.set_update_at(update_at)
            for season in listing.active_children:
                season.set_update_at(update_at)


# TODO: Validate
def _provider_names(file: ProvidersFile) -> set[str]:
    if not file.database_record.content:
        return set()
    return {provider.provider_name for provider in streaming_providers(file.parsed())}
