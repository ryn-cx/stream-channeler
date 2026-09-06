# TODO: Validate
"""What every other part of the plugin reads a Crunchyroll listing by."""

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from chirashi.season_episodes.models import Images as EpisodeImages
from chirashi.series.models import Images as SeriesImages

VIDEO_SOURCE = "Crunchyroll"
MUSIC_SOURCE = "Crunchyroll Music"


# TODO: Validate
class MusicCategory(StrEnum):
    """One of the two listings an artist's releases are split into."""

    MUSIC_VIDEO = "musicvideo"
    CONCERT = "concert"


# The prefix Crunchyroll issues ids under, which is what a key is recognised by.
CATEGORY_ID_PREFIXES = {
    "MV": MusicCategory.MUSIC_VIDEO,
    "MC": MusicCategory.CONCERT,
}

MUSIC_CATEGORY_NAMES = {
    MusicCategory.CONCERT: "Concerts",
    MusicCategory.MUSIC_VIDEO: "Music Videos",
}


# TODO: Validate
def build_url_regex(*path: str, group: str) -> str:
    """Return the regex for a Crunchyroll url."""
    return (
        "(?x:"
        # The sometimes present local prefix like de, pt-br, etc.
        r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"
        # The media type identifier, series, watch, artist, etc.
        + "".join(rf"\/{segment}" for segment in path)
        # The Crunchyroll key.
        + rf"\/(?P<{group}>[A-Z0-9]{{9,}})"
        # The URL suffix, usually a slug but other options are also valid.
        r"(?:[\/?#]|$)"
        ")"
    )


# https://www.crunchyroll.com/watch/musicvideo/MV5CD8B009
MUSIC_VIDEO_URL_REGEX = build_url_regex(
    "watch",
    "musicvideo",
    group="music_video_key",
)
# https://www.crunchyroll.com/watch/concert/MC413F1C5C
CONCERT_URL_REGEX = build_url_regex("watch", "concert", group="concert_key")
# https://www.crunchyroll.com/artist/MA899F54A4
ARTIST_URL_REGEX = build_url_regex("artist", group="artist_key")
# https://www.crunchyroll.com/series/GEXH3W29Z
SERIES_URL_REGEX = build_url_regex("series", group="title_key")
# https://www.crunchyroll.com/watch/GVWU8XW1Z
EPISODE_URL_REGEX = build_url_regex("watch", group="episode_key")


# TODO: Validate
def title_is_a_series(title_key: str) -> bool:
    """Report whether a `Title` key belongs to a series rather than an artist."""
    return title_key.startswith("G")


# TODO: Validate
def season_is_music(season_key: str) -> bool:
    """Report whether a `Season` key is for music."""
    return season_key in set(MusicCategory)


# TODO: Validate
def music_episode_category(episode_key: str) -> MusicCategory:
    """Return the listing an episode is a video or a concert of."""
    return CATEGORY_ID_PREFIXES[episode_key[:2]]


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://crunchyroll.com/{path.lstrip('/')}"


# TODO: Validate
def series_url(title_key: str) -> str:
    return build_url(f"series/{title_key}")


# TODO: Validate
def artist_url(title_key: str) -> str:
    return build_url(f"artist/{title_key}")


# TODO: Validate
def series_episode_url(episode_key: str) -> str:
    return build_url(f"watch/{episode_key}")


# TODO: Validate
def music_episode_url(category: MusicCategory, episode_key: str) -> str:
    return build_url(f"watch/{category}/{episode_key}")


# TODO: Validate
def tenant_category_name(tenant_category: str) -> str:
    return " ".join(word.capitalize() for word in tenant_category.split("-"))


# TODO: Validate
class SizedImage(Protocol):
    width: int
    source: str


# TODO: Validate
def largest_image(images: Sequence[SizedImage]) -> str | None:
    """Return the source of the widest size Crunchyroll offers an image in."""
    if not images:
        return None
    return max(images, key=lambda image: image.width).source


# TODO: Validate
def nearest_thumbnail(images: Sequence[SizedImage]) -> str | None:
    if not images:
        return None
    wide_enough = [image for image in images if image.width >= 480]  # noqa: PLR2004
    if wide_enough:
        return min(wide_enough, key=lambda image: image.width).source
    return max(images, key=lambda image: image.width).source


# TODO: Validate
def title_image(images: SeriesImages) -> str | None:
    """Return the widest poster a listing carries, where it carries one.

    The wide one first because that is the shape the artwork is shown in, the
    tall one being what is left for a listing Crunchyroll has only a portrait
    poster of.
    """
    wide = images.poster_wide
    if wide and wide[0]:
        return max(wide[0], key=lambda image: image.width).source
    tall = images.poster_tall
    if tall and tall[0]:
        return max(tall[0], key=lambda image: image.width).source
    return None


# TODO: Validate
def title_thumbnail(images: SeriesImages) -> str | None:
    wide = images.poster_wide
    if wide and wide[0]:
        return nearest_thumbnail(wide[0])
    tall = images.poster_tall
    if tall and tall[0]:
        return nearest_thumbnail(tall[0])
    return None


# TODO: Validate
def episode_image(images: EpisodeImages) -> str | None:
    """Return the largest thumbnail an episode has, where it has one at all.

    An episode Crunchyroll has no thumbnail for carries no sizes to pick from,
    and older ones carry none of the field at all.
    """
    thumbnails = images.thumbnail
    if not thumbnails or not thumbnails[0]:
        return None
    return thumbnails[0][-1].source


# TODO: Validate
def episode_thumbnail(images: EpisodeImages) -> str | None:
    thumbnails = images.thumbnail
    if not thumbnails or not thumbnails[0]:
        return None
    return nearest_thumbnail(thumbnails[0])
