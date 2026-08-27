# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from datetime import datetime
from typing import override
from urllib.parse import quote_plus

from diving_board.season import models as season_models
from diving_board.series import models as series_models
from diving_board.vod import models as vod_models

from app.shows.models import Show
from plugins.HiDive.constants import (
    MOVIE_MEDIA_TYPE,
    RELEASE_DATE_PREFIX,
    SERIES_MEDIA_TYPE,
)
from plugins.HiDive.files import FileMixin


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
                text = tag.attributes.text
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
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"search?q={quote_plus(query)}")
