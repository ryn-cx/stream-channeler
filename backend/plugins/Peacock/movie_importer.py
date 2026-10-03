# TODO: Validate
"""Writing what Peacock says about a movie into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from plugins.Peacock.constants import TITLE_URL_REGEX
from plugins.Peacock.shared import PeacockImporter
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pigeon.movie.models import MovieModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class PeacockMovieFiles(PeacockImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # A movie is a season of itself, so its own file is what it is read out of.
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
        return [self.movie_season_key(title_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [self.split_season_key(season_key)[0] for season_key in season_keys]

    # TODO: Validate
    @classmethod
    def movie_season_key(cls, title_key: str) -> str:
        # A movie has no seasons of its own so its single season is given a fixed id.
        return cls.build_season_key(title_key, "0")


# TODO: Validate
class PeacockMovieUpsert(PeacockMovieFiles, PeacockImporter, ABC):
    # TODO: Validate
    @override
    def _media_type_channel_key(self) -> str:
        return "Movies"

    # TODO: Validate
    @override
    def _genres(self, title_key: str) -> list[str]:
        return self._movie(title_key).attributes.genres

    # TODO: Validate
    @override
    def _recommendation_urls(self, title_key: str) -> list[str]:
        return self.movie_recommendation_urls(self._movie(title_key))

    # TODO: Validate
    def _movie(self, title_key: str) -> MovieModel:
        return self.movie_file(title_key).parsed()

    # TODO: Validate
    @classmethod
    def movie_recommendation_urls(cls, movie: MovieModel) -> list[str]:
        return [
            cls.asset_url(item.attributes.slug)
            for item in movie.relationships.recs.data
        ]

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.movie_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        attributes = self._movie(title_key).attributes
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=attributes.title,
            description=attributes.synopsis_long,
            media_type=MediaType.movie,
            year=attributes.year,
            url=self.asset_url(attributes.slug),
            image_url=self.landscape_url(attributes.images),
            thumbnail_url=self.landscape_url(attributes.images),
            poster_url=self.poster_url(attributes.images),
            poster_thumbnail_url=self.poster_url(attributes.images),
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(attributes.genres)

        self._upsert_season(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        upserted_title.set_update_at(
            tz_datetime.fromtimestamp(
                attributes.formats.hd.availability.offer_end_ts / 1000,
            ),
        )
        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(self, title: Title) -> None:
        season_key = self.movie_season_key(title.key)
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            season_number=0,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(season_key, title.key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episode(upserted_season, title.key)
        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        existing_episode = Episode.get_from_memory(self.session, season, title_key)
        attributes = self._movie(title_key).attributes
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=attributes.title,
            description=attributes.synopsis_long,
            episode_number=0,
            url=self.asset_url(attributes.slug),
            image_url=self.landscape_url(attributes.images),
            thumbnail_url=self.landscape_url(attributes.images),
            duration=attributes.duration_seconds,
            sort_order=0,
            data_timestamp=self._episode_files_data_timestamp(
                title_key,
                season.key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)


# TODO: Validate
class PeacockMovieImporter(PeacockMovieUpsert):
    pass
