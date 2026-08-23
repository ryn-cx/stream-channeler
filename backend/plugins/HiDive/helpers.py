# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from datetime import datetime
from typing import Any, override
from urllib.parse import quote_plus

from app.shows.models import Show
from plugins.HiDive.files import FileMixin

MOVIE_MEDIA_TYPE = "Movie"
"""What the plugin calls a title that is a film rather than a series."""

SERIES_MEDIA_TYPE = "Series"
"""What the plugin calls a title that is a series rather than a film."""

# What the day a movie came out is written after in the tags of its hero.
_RELEASE_DATE_PREFIX = "Original Premiere: "


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
    def _series_image_url(series_data: dict[str, Any]) -> str:
        """Return the hero image URL from a parsed series file."""
        for element in series_data["elements"]:
            if element["attributes"].get("image"):
                source: str = element["attributes"]["image"]["attributes"]["source"]
                return source
        msg = "No image element found in series file."
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def _movie_title(hero: dict[str, Any]) -> str:
        """Return the movie's title from the VOD's own hero action."""
        for action in hero["attributes"]["actions"]:
            data = action["attributes"]["action"]["data"]
            if data["type"] == "VOD":
                title: str = data["title"]
                return title
        msg = "No VOD action found in movie hero."
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def _movie_description(hero: dict[str, Any]) -> str | None:
        """Return the movie's synopsis from the first hero content block with text."""
        for content in hero["attributes"]["content"]:
            if content["attributes"].get("text"):
                text: str = content["attributes"]["text"]
                return text
        return None

    # TODO: Validate
    @staticmethod
    def _release_date(hero: dict[str, Any]) -> datetime | None:
        """Return the day the title came out, as its hero's tags give it."""
        for content in hero["attributes"]["content"]:
            for tag in content["attributes"].get("tags") or []:
                text = tag["attributes"].get("text")
                if text and text.startswith(_RELEASE_DATE_PREFIX):
                    date_string = text.removeprefix(_RELEASE_DATE_PREFIX)
                    return datetime.strptime(date_string, "%B %d, %Y").astimezone()
        return None

    # TODO: Validate
    @staticmethod
    def _movie_duration(hero: dict[str, Any]) -> int | None:
        """Return how long the movie runs for, in seconds."""
        for content in hero["attributes"]["content"]:
            if content["attributes"].get("duration") is not None:
                duration: int = content["attributes"]["duration"]
                return duration
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
