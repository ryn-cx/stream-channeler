# TODO: Validate
"""Writing what Hulu says about a movie into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Hulu.constants import MOVIE_URL_REGEX, VIDEO_URL_REGEX, HuluMediaType
from plugins.Hulu.shared import (
    HuluImporter,
    build_url,
    episode_url,
    image_url,
    is_collection_season_key,
    thumbnail_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from wholoo.movies.models import Component as MovieComponent

    from app.sources.models import Source
    from plugins.Hulu.files import Movie
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HuluMovieFiles(HuluImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return build_url(f"{HuluMediaType.MOVIE}/{title_key}")

    # TODO: Validate
    @override
    def _media_type_name(self) -> str:
        return "Movies"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[Movie]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _title_components(self, title_key: str) -> Sequence[MovieComponent]:
        return self.movie_file(title_key).components()

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key, *self._collection_season_keys(title_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            if is_collection_season_key(season_key):
                episode_keys += self._collection_episode_keys(season_key, title_key)
            else:
                episode_keys.append(season_key)
        return episode_keys


# TODO: Validate
class HuluMovieUpsert(HuluMovieFiles, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            title_key = match.group("title_key")
        elif match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # The episode.key for a movie is the same as the title.key so this is
            # actually returning a title.key.
            title_key = match.group("episode_key")
        else:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self.raise_invalid_url_if_no_content(self.movie_file(title_key), url)
        return ParsedURL(title_key)

    # TODO: Validate
    @override
    def _title_record(self, source: Source, title_key: str) -> Title:
        parsed_movie = self.movie_file(title_key).details()
        vertical_tile = parsed_movie.entity.artwork.program_vertical_tile
        return Title(
            key=title_key,
            name=parsed_movie.entity.name,
            description=parsed_movie.entity.description,
            year=parsed_movie.entity.premiere_date.year,
            url=self.title_url(title_key),
            image_url=image_url(parsed_movie.entity.artwork.program_tile.path),
            thumbnail_url=thumbnail_url(
                parsed_movie.entity.artwork.program_tile.path,
            ),
            poster_url=image_url(vertical_tile.path if vertical_tile else None),
            poster_thumbnail_url=thumbnail_url(
                vertical_tile.path if vertical_tile else None,
            ),
            media_type=MediaType.movie,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        )

    # TODO: Validate
    @override
    def _upsert_title_seasons(self, title: Title) -> None:
        existing_season = Season.get_from_memory(self.session, title, title.key)
        upserted_season = Season(
            key=title.key,
            season_number=0,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(title.key, title.key),
            title_id=title.id,
        ).upsert(title, existing_season)
        # Movies should be updated from update_show.

        self._upsert_episode(upserted_season)

    # TODO: Validate
    def _upsert_episode(self, season: Season) -> None:
        parsed_movie = self.movie_file(season.key).details()
        existing_episode = Episode.get_from_memory(self.session, season, season.key)
        Episode(
            key=season.key,
            watch_identifier=watch_identifier(self.plugin_name(), season.key),
            name=parsed_movie.entity.name,
            description=parsed_movie.entity.description,
            url=episode_url(season.key),
            image_url=image_url(parsed_movie.entity.artwork.program_tile.path),
            thumbnail_url=thumbnail_url(
                parsed_movie.entity.artwork.program_tile.path,
            ),
            duration=parsed_movie.entity.duration,
            episode_number=0,
            sort_order=0,
            data_timestamp=self._episode_files_data_timestamp(
                season.key,
                season.key,
                season.key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)
        # Movies should be updated from update_show.


# TODO: Validate
class HuluMovieImporter(HuluMovieUpsert):
    pass
