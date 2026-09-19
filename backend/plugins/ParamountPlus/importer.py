# TODO: Validate
"""Writing what Paramount+ says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.shared import ParamountPlusShared
from plugins.ParamountPlus.utils import (
    build_season_key,
    movie_url,
    related_urls,
    split_season_key,
    title_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from trivial_minus.episodes.models import Datum
    from trivial_minus.movie.models import MovieModel
    from trivial_minus.section.models import Datum as SectionDatum
    from trivial_minus.show.models import ShowModel

    from app.sources.models import Source
    from plugins.ParamountPlus.files import SectionFile
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class ParamountPlusImporter(ParamountPlusShared, BaseImporter, ABC):
    pass


# TODO: Validate
class ParamountPlusSeriesImporter(ParamountPlusImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.title_page_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _show(self, title_key: str) -> ShowModel:
        return self.title_page_file(title_key).parsed()

    # TODO: Validate
    def _season_numbers(self, title_key: str) -> list[int]:
        return self._show(title_key).seasons

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_number: int) -> list[Datum]:
        return self.episodes_file(title_key, season_number).parsed().data

    # TODO: Validate
    def _section_files(self, title_key: str) -> list[SectionFile]:
        return [
            self.section_file(title_key, section.id)
            for section in self._show(title_key).sections
        ]

    # TODO: Validate
    def _section_videos(self, title_key: str) -> list[SectionDatum]:
        videos: dict[str, SectionDatum] = {}
        for section_file in self._section_files(title_key):
            for page in section_file.parsed():
                for video in page.data:
                    videos.setdefault(video.content_id, video)
        return list(videos.values())

    # TODO: Validate
    def _genres(self, title_key: str) -> list[str]:
        first_season = self._season_numbers(title_key)[0]
        return list(
            dict.fromkeys(
                episode.genre
                for episode in self._season_episodes(title_key, first_season)
                if episode.genre
            ),
        )

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect new seasons.
        return [self.title_page_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_number = split_season_key(season_key)
        if season_number == 0:
            return self._section_files(title_key)
        # Required to detect new episodes.
        return [self.episodes_file(title_key, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._season_files(season_key, title_key)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        season_keys = [
            build_season_key(title_key, season_number)
            for season_number in self._season_numbers(title_key)
        ]
        if self._show(title_key).sections:
            season_keys.append(build_season_key(title_key, 0))
        return season_keys

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
            _title_key, season_number = split_season_key(season_key)
            if season_number == 0:
                episode_keys += [
                    video.content_id for video in self._section_videos(title_key)
                ]
            else:
                episode_keys += [
                    episode.content_id
                    for episode in self._season_episodes(title_key, season_number)
                ]
        return episode_keys

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        first_season = self._season_numbers(title_key)[0]
        first_episode = self._season_episodes(title_key, first_season)[0]
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=first_episode.series_title,
            media_type=MediaType.series,
            url=title_url(title_key),
            image_url=first_episode.thumb.large,
            thumbnail_url=first_episode.thumb.large,
            data_timestamp=data_timestamp,
            source_id=source.id,
            update_at=data_timestamp + timedelta(days=7),
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(self._genres(title_key))

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        return upserted_title

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        urls = [title.url, *related_urls(self._show(title.key))]
        self.add_new_urls_to_channel("All Titles", urls)
        for genre in self._genres(title.key):
            self.add_new_urls_to_channel(genre, [title.url])

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return related_urls(self._show(title.key))

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        season_numbers = self._season_numbers(title.key)
        for sort_order, season_number in enumerate(season_numbers):
            season_key = build_season_key(title.key, season_number)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            episodes = self._season_episodes(title.key, season_number)
            upserted_season = Season(
                key=season_key,
                name=episodes[0].season_title if episodes else None,
                season_number=season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key, season_number)
            self._set_season_update_at(upserted_season)

        self._upsert_section_season(title, len(season_numbers))

    # TODO: Validate
    def _upsert_section_season(
        self,
        title: Title,
        sort_order: int,
    ) -> None:
        videos = self._section_videos(title.key)
        if not videos:
            return

        season_key = build_season_key(title.key, 0)
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            season_number=0,
            sort_order=sort_order,
            data_timestamp=self._season_files_data_timestamp(
                season_key,
                title.key,
            ),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_section_episodes(upserted_season, title.key, videos)
        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_section_episodes(
        self,
        season: Season,
        title_key: str,
        videos: list[SectionDatum],
    ) -> None:
        for sort_order, video in enumerate(videos):
            episode_key = video.content_id
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=video.title,
                episode_number=sort_order + 1,
                url=video.href.partition("?")[0],
                description=video.description,
                image_url=video.thumb,
                thumbnail_url=video.thumb,
                air_date=video.airdate_iso,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_number: int,
    ) -> None:
        for sort_order, item in enumerate(
            self._season_episodes(title_key, season_number),
        ):
            episode_key = item.content_id
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.title.removeprefix("EPISODE_NAME - ") if item.title else None,
                episode_number=int(item.episode_number),
                url=item.url,
                description=item.description,
                image_url=item.thumb.large,
                thumbnail_url=item.thumb.large,
                duration=item.duration_raw,
                air_date=item.airdate_iso,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class ParamountPlusMovieImporter(ParamountPlusImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

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
    def _movie_data(self, title_key: str) -> MovieModel:
        return self.movie_file(title_key).parsed()

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
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        movie = self._movie_data(title_key)
        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=movie.name,
            description=movie.description,
            media_type=MediaType.movie,
            url=movie_url(title_key),
            image_url=movie.image,
            thumbnail_url=movie.image,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres([movie.genre] if movie.genre else [])

        self._upsert_season(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        self.add_new_urls_to_channel("All Titles", [title.url])
        if genre := self._movie_data(title.key).genre:
            self.add_new_urls_to_channel(genre, [title.url])

    # TODO: Validate
    def _upsert_season(self, title: Title) -> None:
        season_key = build_season_key(title.key, 0)
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
        movie = self._movie_data(title_key)
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=movie.name,
            description=movie.description,
            url=movie_url(title_key),
            image_url=movie.image,
            thumbnail_url=movie.image,
            episode_number=0,
            sort_order=0,
            air_date=movie.date_published,
            data_timestamp=self._episode_files_data_timestamp(
                title_key,
                season.key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)
