# TODO: Validate
"""Writing what HBO Max says about a movie into the database."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.HBOMax.constants import MOVIE_URL_REGEX
from plugins.HBOMax.shared import (
    HBOMaxImporter,
    HBOMaxShared,
    build_season_key,
    movie_content,
    movie_url,
    page_urls,
    related_urls,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from minbo.movie.models import Idref14 as MovieContent

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HBOMaxMovieFiles(HBOMaxShared, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    def _movie_content(self, title_key: str) -> MovieContent:
        return movie_content(self.movie_file(title_key).parsed())

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(title_key)]

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
        return [build_season_key(title_key, 0)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [split_season_key(season_key)[0] for season_key in season_keys]


# TODO: Validate
class HBOMaxMovieUpsert(HBOMaxMovieFiles, HBOMaxImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.movie_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        page = self.movie_file(title.key).parsed()
        urls = [title.url, *page_urls(page)]
        self.add_new_urls_to_channel("All Titles", urls)
        for channel_key in ["Movie", *movie_content(page).genres]:
            self.add_new_urls_to_channel(channel_key, [title.url])

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return related_urls(self.movie_file(title.key).parsed())

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        content = self._movie_content(title_key)
        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=content.title.full,
            description=content.summary.full,
            media_type=MediaType.movie,
            url=movie_url(title_key),
            year=int(content.release_year),
            image_url=content.image_url_link,
            thumbnail_url=content.image_url_link,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(content.genres)

        self._upsert_season(upserted_title, content)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        content: MovieContent,
    ) -> None:
        season_key = build_season_key(title.key, 0)
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            season_number=0,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(season_key, title.key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episode(upserted_season, title.key, content)
        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        content: MovieContent,
    ) -> None:
        existing_episode = Episode.get_from_memory(self.session, season, title_key)
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=content.title.full,
            description=content.summary.full,
            url=movie_url(title_key),
            image_url=content.image_url_link,
            thumbnail_url=content.image_url_link,
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
class HBOMaxMovieImporter(HBOMaxMovieUpsert):
    pass
