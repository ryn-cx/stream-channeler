# TODO: Validate
"""Writing what Paramount+ says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.utils.update_at import staggered_monthly_update_at
from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.shared import ParamountPlusShared
from plugins.ParamountPlus.utils import (
    build_season_key,
    movie_url,
    split_season_key,
    title_url,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trivial_minus.episodes.models import Datum
    from trivial_minus.movie.models import MovieModel

    from app.sources.models import Source
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
    def _season_numbers(self, title_key: str) -> list[int]:
        return self.title_page_file(title_key).parsed().seasons

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_number: int) -> list[Datum]:
        return self.episodes_file(title_key, season_number).parsed().result.data

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect new seasons.
        return [self.title_page_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_number = split_season_key(season_key)
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
        return [
            build_season_key(title_key, season_number)
            for season_number in self._season_numbers(title_key)
        ]

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
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            first_season = self._season_numbers(title_key)[0]
            first_episode = self._season_episodes(title_key, first_season)[0]
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=first_episode.series_title,
                media_type="Series",
                url=title_url(title_key),
                image_url=first_episode.thumb.large,
                thumbnail_url=first_episode.thumb.large,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(min(data_timestamps) + timedelta(days=7))

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_number in enumerate(self._season_numbers(title.key)):
            season_key = build_season_key(title.key, season_number)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                episodes = self._season_episodes(title.key, season_number)
                season = Season(
                    key=season_key,
                    name=episodes[0].season_title if episodes else None,
                    season_number=season_number,
                    sort_order=sort_order,
                    data_timestamp=self._season_files_data_timestamp(
                        season_key,
                        title.key,
                    ),
                    title_id=title.id,
                ).upsert(title, season)
                season.set_update_at(None)

            self._upsert_episodes(season, title.key, season_number, force=force)
            self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(
            self._season_episodes(title_key, season_number),
        ):
            episode_key = item.content_id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
                    key=episode_key,
                    watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                    name=item.title.removeprefix("EPISODE_NAME - ")
                    if item.title
                    else None,
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
                ).upsert(season, episode)
                episode.set_update_at(None)


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
            title_key = match.group("movie_key")
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
        *,
        force: bool = False,
    ) -> Title:
        movie = self._movie_data(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=movie.name,
                description=movie.description,
                media_type="Movie",
                url=movie_url(title_key),
                image_url=movie.image,
                thumbnail_url=movie.image,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, min(data_timestamps)),
            )

        self._upsert_season(title, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return title

    # TODO: Validate
    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season_key = build_season_key(title.key, 0)
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title.key, force=force):
            season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(season_key, title.key),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)

        self._upsert_episode(season, title.key, force=force)
        self._set_season_update_at_based_on_last_episode(season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if self._episode_is_outdated(
            episode,
            season.key,
            title_key,
            force=force,
        ):
            movie = self._movie_data(title_key)
            episode = Episode(
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
            ).upsert(season, episode)
            episode.set_update_at(None)
