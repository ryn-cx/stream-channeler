# TODO: Validate
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, Literal, override

from diving_board import DivingBoard
from diving_board.schedule import models as schedule_models
from diving_board.search import models as search_models
from diving_board.season import models as season_models
from diving_board.series import models as series_models
from diving_board.vod import models as vod_models
from diving_board.vod.hero.models import VodHeroModel
from sqlmodel import Session

from app.files.models import File
from app.plugins.models import Plugin
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import (
    GAPIJSON,
    BaseFile,
    GAPIListJSON,
    PartialGAPIJSON,
)
from plugins.utils.get_around_client import get_around_client


@cache
def diving_board() -> DivingBoard:
    return DivingBoard(get_around_client=get_around_client())


class Season(PartialGAPIJSON[season_models.SeasonModel]):
    # Occurs when the user imports an invalid TV show url.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = diving_board().season

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> season_models.SeasonModel:
        return diving_board().season.download_and_parse(int(self.unique_identifier))


class Vod(PartialGAPIJSON[vod_models.VodModel]):
    # Occurs when the user imports an invalid movie url.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = diving_board().vod

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> vod_models.VodModel:
        return diving_board().vod.download_and_parse(int(self.unique_identifier))


class Series(PartialGAPIJSON[series_models.SeriesModel]):
    # Occurs when the user imports an invalid series url.
    ACCEPTABLE_ERROR = "Unexpected response status code: 404"
    API_ENDPOINT = diving_board().series

    @override
    # TODO: Make Diving Board support a str as an input so _get is not needed.
    def _get(self) -> series_models.SeriesModel:
        return diving_board().series.download_and_parse(int(self.unique_identifier))


class Schedule(GAPIListJSON[schedule_models.ScheduleModel]):
    API_ENDPOINT = diving_board().schedule

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        input_date: datetime,
    ) -> None:
        self.input_date = input_date
        super().__init__(session, plugin, input_date.isoformat())

    @override
    def _get(self) -> list[schedule_models.ScheduleModel]:
        # Start at the first of the month because it matches the normal API calls.
        from_ = self.input_date.replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return diving_board().schedule.download_and_parse_until_datetime(
            from_=from_,
            end_datetime=tz_datetime.now(),
        )


class Search(GAPIJSON[search_models.SearchModel]):
    API_ENDPOINT = diving_board().search


class HiDiveFiles(TMDBMixin, register=False):
    _media_type_value: str | None = None

    def _is_movie(self) -> bool:
        if self._media_type_value not in ("Movie", "Series"):
            msg = f"Invalid media type: {self._media_type_value}"
            raise RuntimeError(msg)

        return self._media_type_value == "Movie"

    def season_file(self, season_key: str | int) -> Season:
        """Return a cached Season for the given season key."""
        key = str(season_key)
        return self._get_cached_file(
            Season,
            key,
            lambda: Season(self.session, self.plugin, key),
        )

    def vod_file(self, vod_key: str | int) -> Vod:
        """Return a cached Vod for the given vod key."""
        key = str(vod_key)
        return self._get_cached_file(
            Vod,
            key,
            lambda: Vod(self.session, self.plugin, key),
        )

    def series_file(self, series_key: str | int) -> Series:
        """Return a cached Series for the given series key."""
        key = str(series_key)
        return self._get_cached_file(
            Series,
            key,
            lambda: Series(self.session, self.plugin, key),
        )

    def schedule_file(self, input_date: datetime | File) -> Schedule:
        """Return a cached Schedule for the given datetime or existing File."""
        if isinstance(input_date, File):
            input_date = datetime.fromisoformat(
                Schedule.file_key_to_unique_identifier(input_date.key),
            )
        return self._get_cached_file(
            Schedule,
            input_date,
            lambda: Schedule(self.session, self.plugin, input_date),
        )

    def search_file(self, query: str) -> Search:
        """Return a cached Search for the given query."""
        return self._get_cached_file(
            Search,
            query,
            lambda: Search(self.session, self.plugin, query),
        )

    def get_latest_schedule_file(self) -> Schedule | None:
        """Return the latest schedule file, or None if none exists."""
        if file := self.preload_latest_file(Schedule):
            return self.schedule_file(file)
        return None

    @override
    def _source_files(self) -> Sequence[Schedule]:
        if file := self.get_latest_schedule_file():
            return [file]
        return []

    @staticmethod
    def _series_season_items(
        series_data: series_models.SeriesModel,
    ) -> list[series_models.Item1]:
        """Return the list of seasons from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.seasons:
                return element.attributes.seasons.items
        msg = "No seasons element found in series file."
        raise ValueError(msg)

    @staticmethod
    def _series_image_url(series_data: series_models.SeriesModel) -> str:
        """Return the hero image URL from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.image:
                return element.attributes.image.attributes.source
        msg = "No image element found in series file."
        raise ValueError(msg)

    @staticmethod
    def _movie_title(hero: VodHeroModel) -> str:
        """Return the movie's title from the VOD's own hero action."""
        for action in hero.attributes.actions:
            data = action.attributes.action.data
            if data.type == "VOD":
                return data.title
        msg = "No VOD action found in movie hero."
        raise ValueError(msg)

    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        media_type: Literal["movie", "tv"]
        if self._is_movie():
            self.vod_file(show_key).download_if_outdated()
            hero = diving_board().vod.extract_hero(self.vod_file(show_key).parsed())
            name = self._movie_title(hero)
            media_type = "movie"
        else:
            self.series_file(show_key).download_if_outdated()
            name = self.series_file(show_key).parsed().metadata.series.title
            media_type = "tv"
        return self._tmdb_search_media(name, media_type)

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        if self._is_movie():
            return None
        for season_info in self._series_season_items(
            self.series_file(show_key).parsed(),
        ):
            if str(season_info.id) == season_key:
                return season_info.season_number
        return None

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        if self._is_movie():
            return None
        bucket = diving_board().season.extract_bucket_season(
            self.season_file(season_key).parsed(),
        )
        for item in bucket.attributes.items:
            if str(item.id) == episode_key:
                match = re.match(r"^E(\d+)", item.title) if item.title else None
                return int(match.group(1)) if match else None
        return None

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie() else "tv"

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.vod_file(show_key)]
        else:
            base_files = [self.series_file(show_key)]
        return self._append_tmdb_show_file(base_files, show_key)

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.vod_file(season_key)]
        else:
            # The season file detects new episodes and changes to the season.
            base_files = [self.season_file(season_key)]
        return self._append_tmdb_season_file(base_files, season_key, show_key)

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        base_files: list[BaseFile[Any]]
        if self._is_movie():
            base_files = [self.vod_file(episode_key)]
        else:
            # The vod file detects changes to the episode information.
            base_files = [self.vod_file(episode_key), self.season_file(season_key)]
        return self._append_tmdb_episode_file(
            base_files,
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [show_key]
        series_data = self.series_file(show_key).parsed()
        return [str(item.id) for item in self._series_season_items(series_data)]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        if self._is_movie():
            return list(season_keys)
        episode_keys: list[str] = []
        for season_key in season_keys:
            season_data = self.season_file(season_key).parsed()
            bucket = diving_board().season.extract_bucket_season(season_data)
            episode_keys.extend(str(item.id) for item in bucket.attributes.items)
        return episode_keys
