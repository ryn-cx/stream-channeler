# TODO: Validate
"""Writing what Netflix says about a movie into the database."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Netflix.shared import NetflixImporter, NetflixShared
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from meshfilm.detail_modal.models import DetailModalModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NetflixMovieFiles(NetflixShared, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.title_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        return [title_key]


# TODO: Validate
class NetflixMovieUpsert(NetflixMovieFiles, NetflixImporter, ABC):
    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        movie_data = self.title_file(title_key).parsed()
        existing_title = Title.get_from_memory(self.session, source, title_key)
        upserted_title = Title(
            key=title_key,
            name=movie_data.title,
            url=self.title_url(title_key),
            year=movie_data.latest_year,
            image_url=movie_data.boxart_high_res.url,
            thumbnail_url=movie_data.boxart.url,
            media_type=MediaType.movie,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(self._genre_names(movie_data))

        self._upsert_season(upserted_title, movie_data)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        movie_data: DetailModalModel,
    ) -> None:
        season_key = title.key
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            season_number=0,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(season_key, title.key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episode(upserted_season, title.key, movie_data)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        movie_data: DetailModalModel,
    ) -> None:
        existing_episode = Episode.get_from_memory(self.session, season, title_key)
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=movie_data.title,
            url=self.episode_url(title_key),
            image_url=movie_data.boxart_high_res.url,
            thumbnail_url=movie_data.boxart.url,
            episode_number=0,
            sort_order=0,
            data_timestamp=self._episode_files_data_timestamp(
                title_key,
                season.key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)


# TODO: Validate
class NetflixMovieImporter(NetflixMovieUpsert):
    pass
