# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from datetime import datetime
from typing import override
from urllib.parse import quote_plus

from diving_board.schedule import models as schedule_models
from diving_board.season import models as season_models
from diving_board.series import models as series_models
from diving_board.vod import models as vod_models

from app.shows.models import Show
from app.utils import tz_datetime
from plugins.HiDive.constants import (
    DETAIL_MAX_AGE,
    MOVIE_MEDIA_TYPE,
    RELEASE_DATE_PREFIX,
    SERIES_MEDIA_TYPE,
)
from plugins.HiDive.files import FileMixin, single_element
from plugins.utils.abstract_plugin import PluginShowIdentity


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
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and what its files say about it."""

    # TODO: Validate
    @override
    def _set_media_type_from_show(self, show: Show) -> None:
        if not show.media_type:
            msg = "Show.media_type is not set."
            raise AttributeError(msg)
        self._media_type_value = show.media_type

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
    @classmethod
    def _show_url(cls, key: str | int, media_type: str = SERIES_MEDIA_TYPE) -> str:
        if media_type == MOVIE_MEDIA_TYPE:
            return cls.build_url(f"video/{key}")
        return cls.build_url(f"series/{key}")

    # TODO: Validate
    @classmethod
    def _season_url(cls, season_key: str | int) -> str:
        return cls.build_url(f"season/{season_key}")

    # TODO: Validate
    @classmethod
    def _episode_url(cls, episode_key: str | int) -> str:
        return cls.build_url(f"video/{episode_key}")

    # TODO: Validate
    @override
    @classmethod
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        if self._is_movie():
            return self._movie_identity(show_key)
        return self._series_identity(show_key)

    # TODO: Validate
    def _series_identity(self, show_key: str) -> PluginShowIdentity:
        series_file = self.series_file(show_key)
        series_file.download_if_outdated(tz_datetime.now() - DETAIL_MAX_AGE)
        return PluginShowIdentity(
            title=series_file.parsed().metadata.series.title,
            media_type=SERIES_MEDIA_TYPE,
        )

    # TODO: Validate
    def _movie_identity(self, show_key: str) -> PluginShowIdentity:
        vod_file = self.vod_file(show_key)
        vod_file.download_if_outdated(tz_datetime.now() - DETAIL_MAX_AGE)
        hero = vod_hero(vod_file.parsed())
        release_date = self._release_date(hero)
        return PluginShowIdentity(
            title=self._movie_title(hero),
            media_type=MOVIE_MEDIA_TYPE,
            year=release_date.year if release_date else None,
        )
