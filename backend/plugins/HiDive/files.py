# TODO: Validate
"""The files a HiDive title is read out of."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cache
from typing import Any, override

from diving_board import DivingBoard
from diving_board.exceptions import (
    SeasonNotFoundError,
    SeriesNotFoundError,
    VodNotFoundError,
)
from diving_board.schedule import Schedule as ScheduleEndpoint
from diving_board.schedule import models as schedule_models
from diving_board.search import Search as SearchEndpoint
from diving_board.search import models as search_models
from diving_board.season import Season as SeasonEndpoint
from diving_board.season import models as season_models
from diving_board.series import Series as SeriesEndpoint
from diving_board.series import models as series_models
from diving_board.vod import Vod as VodEndpoint
from diving_board.vod import models as vod_models

from app.files.models import File
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.HiDive.constants import (
    MOVIE_MEDIA_TYPE,
    RELEASE_DATE_PREFIX,
    SERIES_MEDIA_TYPE,
)
from plugins.utils.abstract_plugin import PluginShowIdentity
from plugins.utils.base_plugin_v2.base import PluginBase
from plugins.utils.base_plugin_v2.files import (
    BaseFile,
    EndpointFile,
    PagedEndpointFile,
)
from plugins.utils.base_plugin_v2.media_type import MediaTypeMixin
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def diving_board() -> DivingBoard:
    """Return a cached Diving Board client."""
    return DivingBoard(get_around_client=get_around_client())


# TODO: Validate
def single_element[ElementT](elements: list[ElementT], description: str) -> ElementT:
    if not elements:
        msg = f"No {description} element found"
        raise ValueError(msg)
    if len(elements) > 1:
        msg = f"Too many {description} elements found"
        raise ValueError(msg)
    return elements[0]


# TODO: Validate
def _tag_text(tag: vod_models.Tag) -> str | None:
    text = tag.attributes.text
    if text is None or isinstance(text, str):
        return text
    return text.attributes.text


# TODO: Validate
def vod_hero(vod_data: vod_models.VodModel) -> vod_models.Element:
    """Return the hero element of a parsed vod file."""
    return single_element(
        [element for element in vod_data.elements if element.field_type == "hero"],
        "hero",
    )


# TODO: Validate
def season_hero(season_data: season_models.SeasonModel) -> season_models.Element:
    """Return the hero element of a parsed season file."""
    return single_element(
        [element for element in season_data.elements if element.field_type == "hero"],
        "hero",
    )


# TODO: Validate
def schedule_group_list(
    schedule_data: schedule_models.ScheduleModel,
) -> schedule_models.Element:
    """Return the element a page of the schedule lists its days in."""
    return single_element(
        [
            element
            for element in schedule_data.elements
            if element.field_type == "groupList"
        ],
        "groupList",
    )


# TODO: Validate
def season_bucket(season_data: season_models.SeasonModel) -> season_models.Element:
    """Return the element a season's own episodes are listed in."""
    return single_element(
        [
            element
            for element in season_data.elements
            if element.field_type == "bucket" and element.attributes.type == "season"
        ],
        "'season' bucket",
    )


# TODO: Validate
class Season(EndpointFile[season_models.SeasonModel]):
    """Season file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return diving_board().season

    # Occurs when the user imports an invalid TV show url.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeasonNotFoundError)


# TODO: Validate
class Vod(EndpointFile[vod_models.VodModel]):
    """Vod file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> VodEndpoint:
        return diving_board().vod

    # Occurs when the user imports an invalid movie url.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, VodNotFoundError)


# TODO: Validate
class Series(EndpointFile[series_models.SeriesModel]):
    """Series file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> SeriesEndpoint:
        return diving_board().series

    # Occurs when the user imports an invalid series url.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class Schedule(PagedEndpointFile[schedule_models.ScheduleModel]):
    """Schedule file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> ScheduleEndpoint:
        return diving_board().schedule

    # TODO: Validate
    @override
    def _download_pages(self) -> list[str]:
        # Start at the first of the month because it matches the normal API calls.
        from_ = self.identifier_datetime().replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        return self._endpoint().download_all(from_)


# TODO: Validate
class Search(EndpointFile[search_models.SearchModel]):
    """Search file."""

    # TODO: Validate
    @override
    def _endpoint(self) -> SearchEndpoint:
        return diving_board().search

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


# TODO: Validate
class FileMixin(MediaTypeMixin, PluginBase):
    """The files a title is read out of."""

    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type = show.media_type

    # TODO: Validate
    @staticmethod
    def _series_image_url(series_data: series_models.SeriesModel) -> str:
        """Return the hero image URL from a parsed series file."""
        for element in series_data.elements:
            if element.attributes.image:
                return element.attributes.image.attributes.source
        msg = "No image element found in series file."
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def _hero_image_url(hero: season_models.Element | vod_models.Element) -> str:
        """Return the image URL a hero is illustrated with."""
        if not hero.attributes.image:
            msg = "No image found in hero element."
            raise ValueError(msg)
        return hero.attributes.image.attributes.source

    # TODO: Validate
    @staticmethod
    def _movie_title(hero: vod_models.Element) -> str:
        """Return the movie's title from the VOD's own hero action."""
        for action in hero.attributes.actions or []:
            data = action.attributes.action.data
            if data.type == "VOD":
                return data.title
        msg = "No VOD action found in movie hero."
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def _movie_description(hero: vod_models.Element) -> str | None:
        """Return the movie's synopsis from the first hero content block with text."""
        for content in hero.attributes.content or []:
            if content.attributes.text:
                return content.attributes.text
        return None

    # TODO: Validate
    @staticmethod
    def _release_date(hero: vod_models.Element) -> datetime | None:
        """Return the day the title came out, as its hero's tags give it."""
        for content in hero.attributes.content or []:
            for tag in content.attributes.tags or []:
                text = _tag_text(tag)
                if text and text.startswith(RELEASE_DATE_PREFIX):
                    date_string = text.removeprefix(RELEASE_DATE_PREFIX)
                    return datetime.strptime(date_string, "%B %d, %Y").astimezone()
        return None

    # TODO: Validate
    @staticmethod
    def _movie_duration(hero: vod_models.Element) -> int | None:
        """Return how long the movie runs for, in seconds."""
        for content in hero.attributes.content or []:
            if content.attributes.duration is not None:
                return content.attributes.duration
        return None

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        if self._is_movie():
            return self._movie_identity(show_key)
        return self._series_identity(show_key)

    # TODO: Validate
    def _series_identity(self, show_key: str) -> PluginShowIdentity:
        series_file = self.series_file(show_key)
        series_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return PluginShowIdentity(
            title=series_file.parsed().metadata.series.title,
            media_type=SERIES_MEDIA_TYPE,
        )

    # TODO: Validate
    def _movie_identity(self, show_key: str) -> PluginShowIdentity:
        vod_file = self.vod_file(show_key)
        vod_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        hero = vod_hero(vod_file.parsed())
        release_date = self._release_date(hero)
        return PluginShowIdentity(
            title=self._movie_title(hero),
            media_type=MOVIE_MEDIA_TYPE,
            year=release_date.year if release_date else None,
        )

    # TODO: Validate
    def _is_movie(self) -> bool:
        if self._media_type not in ("Movie", "Series"):
            msg = f"Invalid media type: {self._media_type}"
            raise RuntimeError(msg)

        return self._media_type == "Movie"

    # TODO: Validate
    def season_file(self, season_key: str | int) -> Season:
        """Return a cached Season for the given season key."""
        key = str(season_key)
        return self._file(Season, key)

    # TODO: Validate
    def vod_file(self, vod_key: str | int) -> Vod:
        """Return a cached Vod for the given vod key."""
        key = str(vod_key)
        return self._file(Vod, key)

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        """Return a cached Search for the given query."""
        return self._file(Search, query)

    # TODO: Validate
    def series_file(self, series_key: str | int) -> Series:
        """Return a cached Series for the given series key."""
        key = str(series_key)
        return self._file(Series, key)

    # TODO: Validate
    def schedule_file(self, input_date: datetime | File) -> Schedule:
        """Return a cached Schedule for the given datetime or existing File."""
        if isinstance(input_date, File):
            identifier = Schedule.file_key_to_unique_identifier(input_date.key)
        else:
            identifier = input_date.isoformat()
        return self._file(Schedule, identifier)

    # TODO: Validate
    def get_latest_schedule_file(self) -> Schedule | None:
        """Return the latest schedule file, or None if none exists."""
        if file := self.preload_latest_file(Schedule):
            return self.schedule_file(file)
        return None

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[Schedule]:
        if file := self.get_latest_schedule_file():
            return [file]
        return []

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.vod_file(show_key)]
        return [self.series_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.vod_file(season_key)]
        # The season file detects new episodes and changes to the season.
        return [self.season_file(season_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if self._is_movie():
            return [self.vod_file(episode_key)]
        # The vod file detects changes to the episode information.
        return [self.vod_file(episode_key), self.season_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        if self._is_movie():
            return [show_key]
        series_data = self.series_file(show_key).parsed()
        return [str(item.id) for item in self._series_season_items(series_data)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        if self._is_movie():
            return list(season_keys)
        episode_keys: list[str] = []
        for season_key in season_keys:
            season_data = self.season_file(season_key).parsed()
            bucket = season_bucket(season_data)
            episode_keys.extend(str(item.id) for item in bucket.attributes.items or [])
        return episode_keys
