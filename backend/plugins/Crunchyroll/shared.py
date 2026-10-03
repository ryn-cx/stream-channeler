# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, override

from plugins.Crunchyroll.constants import (
    ARTIST_URL_REGEX,
    CONCERT_URL_REGEX,
    EPISODE_URL_REGEX,
    MUSIC_VIDEO_URL_REGEX,
    SERIES_URL_REGEX,
    CrunchyrollMusicCategory,
)
from plugins.utils.base_plugin.core import BasePluginCore

# The prefix Crunchyroll issues ids under, which is what a key is recognised by.
CATEGORY_ID_PREFIXES = {
    "MV": CrunchyrollMusicCategory.MUSIC_VIDEO,
    "MC": CrunchyrollMusicCategory.CONCERT,
}


# TODO: Validate
def title_is_a_series(title_key: str) -> bool:
    """Report whether a `Title` key belongs to a series rather than an artist."""
    return title_key.startswith("G")


# TODO: Validate
def season_is_music(season_key: str) -> bool:
    """Report whether a `Season` key is for music."""
    return season_key in set(CrunchyrollMusicCategory)


# TODO: Validate
class CrunchyrollSizedImage(Protocol):
    width: int
    source: str


# TODO: Validate
class CrunchyrollShared(BasePluginCore):
    # TODO: Validate
    @staticmethod
    def nearest_thumbnail(images: Sequence[CrunchyrollSizedImage]) -> str | None:
        if not images:
            return None
        wide_enough = [image for image in images if image.width >= 480]  # noqa: PLR2004
        if wide_enough:
            return min(wide_enough, key=lambda image: image.width).source
        return max(images, key=lambda image: image.width).source

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Crunchyroll"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://crunchyroll.com/build/assets/img/favicons/favicon-v2-96x96.png"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            MUSIC_VIDEO_URL_REGEX,  # Must be listed first due to regex overlap.
            CONCERT_URL_REGEX,
            ARTIST_URL_REGEX,
            SERIES_URL_REGEX,
            EPISODE_URL_REGEX,
        )
