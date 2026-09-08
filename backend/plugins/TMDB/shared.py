# TODO: Validate

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from itertools import pairwise
from typing import override

from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel

from app.canonical_media.tmdb import (
    chosen_group_id,
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
)
from app.media.media_type import TMDBMediaType
from app.plugins.schemas import TMDBMediaInfo
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.TMDB.files import WatchProvidersFile
from plugins.TMDB.search import TMDBSearch
from plugins.TMDB.utils import (
    TMDBSeasonInfo,
    get_media_plugin,
    streaming_providers,
)
from plugins.utils.base_plugin.files import COMPLETED_STATUS


# TODO: Validate
def provider_names(file: WatchProvidersFile) -> set[str]:
    """Return the names of all providers in a WatchProviders file."""
    return {provider.provider_name for provider in streaming_providers(file.parsed())}


# TODO: Validate
class TMDBShared(TMDBSearch):
    """Reads TMDB into records of TMDB's own.

    A season and an episode are keyed by their own TMDB ids, which is what
    names them wherever they are spoken about, while the API is asked for them
    by the numbering they have within the title. The files already downloaded
    are what turn one into the other, so the numbering is read back rather
    than carried around in the key.
    """

    # TODO: Validate
    @classmethod
    @override
    def link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    @staticmethod
    def _watch_providers_due(record: Title) -> bool:
        if record.update_at is None:
            return False
        return record.update_at <= tz_datetime.now()

    # TODO: Validate
    def media_info(self, media_identifier: str) -> TMDBMediaInfo:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(media_identifier)
        if media_type == TMDBMediaType.movie:
            return TMDBMediaInfo(
                detail=self.movies_details_file(tmdb_media_id).parsed(),
                watch_providers=self.latest_movies_watch_providers_file(
                    tmdb_media_id,
                )
                .parsed()
                .results.us,
            )
        return TMDBMediaInfo(
            detail=self.tv_series_details_file(tmdb_media_id).parsed(),
            watch_providers=self.latest_tv_series_watch_providers_file(
                tmdb_media_id,
            )
            .parsed()
            .results.us,
        )

    # TODO: Validate
    def _chosen_episode_group(
        self,
        title_key: str,
    ) -> TvEpisodeGroupDetailsModel | None:
        title = Title.get(self.session, self.source, title_key)
        if title and (group_id := chosen_group_id(title.extra)):
            return self.tv_episode_groups_details_file(group_id).parsed()
        return None

    # TODO: Validate
    def chosen_seasons(
        self,
        title_key: str,
    ) -> list[TMDBSeasonInfo]:
        """Return the seasons for the title.

        If the title uses an episode_group the the seasons will be based on the contents
        of TVEpisodeGroupsDetails.

        If the title does not use an episode_group the seasons will be based on the
        contents of TVSeriesDetails.
        """

        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)

        if group := self._chosen_episode_group(title_key):
            return [
                TMDBSeasonInfo.from_episode_group(order, entry)
                for order, entry in enumerate(group.groups)
            ]

        return [
            TMDBSeasonInfo.from_season_details(
                self.tv_seasons_details_file(
                    tmdb_tv_title_id=tmdb_tv_title_id,
                    season_number=season.season_number,
                ).parsed(),
            )
            for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons
        ]

    # TODO: Validate
    def _native_season_number(self, season_key: str, title_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons:
            if season.id == tmdb_tv_season_id:
                return season.season_number
        message = f"{title_key} has no season {season_key}"
        raise ValueError(message)

    # TODO: Validate
    def _process_watch_providers(
        self,
        title_key: str,
        files: Sequence[WatchProvidersFile],
    ) -> None:
        """Process all of the supplied WatchProvider files for a single title."""
        for old_watch_providers_files, new_watch_providers_file in pairwise(files):
            changed_watch_providers = provider_names(
                file=old_watch_providers_files,
            ) ^ provider_names(
                file=new_watch_providers_file,
            )
            for changed_watch_provider in changed_watch_providers:
                self._process_changed_provider(
                    title_key=title_key,
                    changed_provider=changed_watch_provider,
                    update_at=new_watch_providers_file.data_timestamp(),
                )
            record = old_watch_providers_files.database_record
            record.status = COMPLETED_STATUS
            record.update_at = None

    # TODO: Validate
    def _process_changed_provider(
        self,
        title_key: str,
        changed_provider: str,
        update_at: datetime,
    ) -> None:
        """Process a single changed provider.

        Sets the title.updated_at and season.updated_at values."""
        if plugin := get_media_plugin(changed_provider):
            canonical_title = Title.get_one(self.session, self.source, title_key)
            for canonical_link in canonical_title.non_canonical_title_links:
                if (
                    canonical_link.non_canonical_title.source.plugin.key
                    == plugin.plugin_name()
                ):
                    # Watch provider status changing warrants a complete updates of both
                    # the title and season files for simplicity.
                    canonical_link.non_canonical_title.set_update_at(update_at, [])
                    for season in canonical_link.non_canonical_title.active_children:
                        season.set_update_at(update_at, [])

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "TMDB"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "themoviedb.org"
