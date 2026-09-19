# TODO: Validate
"""Writing what TMDB says about a movie into the database."""

from __future__ import annotations

import re
from abc import ABC
from collections.abc import Sequence
from typing import Any, override

from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import (
    watch_identifier,
)
from app.tmdb_media.tmdb import (
    get_media_type_and_tmdb_id,
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_title_key,
)
from app.utils import tz_datetime
from plugins.TMDB.constants import MOVIE_URL_REGEX
from plugins.TMDB.shared import (
    TMDBImporter,
    TMDBShared,
    clean_air_datetime,
    image_url,
    parse_release_year,
    runtime_in_seconds,
    thumbnail_url,
    tmdb_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL


# TODO: Validate
class TMDBMovieFiles(TMDBShared, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        media_type, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [tmdb_season_key(media_type, tmdb_movie_id)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        media_type, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [tmdb_episode_key(media_type, tmdb_movie_id)]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [
            self.movies_details_file(tmdb_movie_id),
            self.movies_watch_providers_file(tmdb_movie_id),
        ]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [self.movies_details_file(tmdb_movie_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        return [self.movies_details_file(tmdb_movie_id)]


# TODO: Validate
class TMDBMovieUpsert(TMDBMovieFiles, TMDBImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        regex_match = re.match(self._domains_regex() + MOVIE_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_movie_id = int(regex_match.group("title_key"))
        self.raise_invalid_url_if_no_content(
            self.movies_details_file(tmdb_movie_id),
            url,
        )
        return ParsedURL(tmdb_title_key(TMDBMediaType.movie, tmdb_movie_id))

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        _, tmdb_movie_id = get_media_type_and_tmdb_id(title_key)
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        existing_title = Title.get_from_memory(self.session, source, title_key)
        upserted_title = Title(
            key=title_key,
            name=parsed_movie_details.title,
            description=parsed_movie_details.overview,
            url=tmdb_url(TMDBMediaType.movie, tmdb_movie_id),
            image_url=image_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            thumbnail_url=thumbnail_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            poster_url=image_url(parsed_movie_details.poster_path),
            poster_thumbnail_url=thumbnail_url(parsed_movie_details.poster_path),
            year=parse_release_year(parsed_movie_details.release_date),
            score=parsed_movie_details.vote_average,
            popularity=parsed_movie_details.popularity,
            original_language=parsed_movie_details.original_language,
            media_type=MediaType.movie,
            data_timestamp=self._title_files_data_timestamp(title_key),
            tmdb_title_validated_at=tz_datetime.now(),
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(
            genre.name for genre in parsed_movie_details.genres
        )
        upserted_title.set_spoken_languages(
            {
                language.iso_639_1: language.english_name
                for language in parsed_movie_details.spoken_languages
            },
        )

        self._upsert_season(upserted_title, title_key, tmdb_movie_id)
        movie_watch_providers = self.movies_watch_providers_file(tmdb_movie_id).parsed()
        self._record_unmatched_providers(upserted_title, movie_watch_providers)
        self._record_watch_providers(upserted_title, movie_watch_providers)
        return upserted_title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
        tmdb_movie_id: int,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        season_key = tmdb_season_key(TMDBMediaType.movie, tmdb_movie_id)
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            name=parsed_movie_details.title,
            season_number=0,
            sort_order=0,
            image_url=image_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            thumbnail_url=thumbnail_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            data_timestamp=self._season_files_data_timestamp(season_key, title_key),
            title_id=title.id,
            update_at=None,
        ).upsert(title, existing_season)

        self._upsert_episode(
            season=upserted_season,
            season_key=season_key,
            title_key=title_key,
            tmdb_movie_id=tmdb_movie_id,
        )

        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        season_key: str,
        title_key: str,
        tmdb_movie_id: int,
    ) -> None:
        parsed_movie_details = self.movies_details_file(tmdb_movie_id).parsed()
        episode_key = tmdb_episode_key(TMDBMediaType.movie, tmdb_movie_id)
        existing_episode = Episode.get_from_memory(self.session, season, episode_key)
        Episode(
            key=episode_key,
            watch_identifier=watch_identifier(self.plugin_name(), episode_key),
            name=parsed_movie_details.title,
            description=parsed_movie_details.overview,
            url=tmdb_url(TMDBMediaType.movie, tmdb_movie_id),
            image_url=image_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            thumbnail_url=thumbnail_url(
                parsed_movie_details.backdrop_path or parsed_movie_details.poster_path,
            ),
            duration=runtime_in_seconds(parsed_movie_details.runtime),
            air_date=clean_air_datetime(parsed_movie_details.release_date),
            episode_number=0,
            sort_order=0,
            data_timestamp=self._episode_files_data_timestamp(
                episode_key,
                season_key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)


# TODO: Validate
class TMDBMovie(TMDBMovieUpsert):
    pass
