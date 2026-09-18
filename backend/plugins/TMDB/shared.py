# TODO: Validate

from __future__ import annotations

from typing import override

from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel

from app.media.media_type import TMDBMediaType
from app.plugins.schemas import TMDBMediaInfo
from app.titles.models import Title
from app.tmdb_media.tmdb import (
    chosen_group_id,
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
)
from plugins.TMDB.search import TMDBSearch
from plugins.TMDB.utils import TMDBSeasonInfo


# TODO: Validate
class TMDBShared(TMDBSearch):
    # TODO: Validate
    @classmethod
    @override
    def _link_to_tmdb(cls) -> bool:
        return False

    # TODO: Validate
    def media_info(self, media_identifier: str) -> TMDBMediaInfo:
        media_type, tmdb_media_id = get_media_type_and_tmdb_id(media_identifier)
        if media_type == TMDBMediaType.movie:
            movie_details_file = self.movies_details_file(tmdb_media_id)
            movie_providers_file = self.movies_watch_providers_file(tmdb_media_id)
            self._download_if_outdated([movie_details_file, movie_providers_file])
            return TMDBMediaInfo(
                detail=movie_details_file.parsed(),
                watch_providers=movie_providers_file.parsed().results.us,
            )

        series_details_file = self.tv_series_details_file(tmdb_media_id)
        series_providers_file = self.tv_series_watch_providers_file(tmdb_media_id)
        self._download_if_outdated([series_details_file, series_providers_file])
        return TMDBMediaInfo(
            detail=series_details_file.parsed(),
            watch_providers=series_providers_file.parsed().results.us,
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

        season_files = [
            self.tv_seasons_details_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=season.season_number,
            )
            for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons
        ]
        self._download_if_outdated(season_files)
        return [
            TMDBSeasonInfo.from_season_details(season_file.parsed())
            for season_file in season_files
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
