# TODO: Validate
"""What every other part of the plugin reads a Crunchyroll listing by."""

from collections.abc import Sequence
from typing import Protocol

from chirashi.season_episodes.models import Images as EpisodeImages
from chirashi.series.models import Images as SeriesImages
from chirashi.series.models import SeriesModel

from plugins.Crunchyroll.constants import CrunchyrollMusicCategory

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
def music_episode_category(episode_key: str) -> CrunchyrollMusicCategory:
    """Return the listing an episode is a video or a concert of."""
    return CATEGORY_ID_PREFIXES[episode_key[:2]]


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://crunchyroll.com/{path.lstrip('/')}"


# TODO: Validate
class CrunchyrollSizedImage(Protocol):
    width: int
    source: str


# TODO: Validate
def largest_image(images: Sequence[CrunchyrollSizedImage]) -> str | None:
    """Return the source of the widest size Crunchyroll offers an image in."""
    if not images:
        return None
    return max(images, key=lambda image: image.width).source


# TODO: Validate
def nearest_thumbnail(images: Sequence[CrunchyrollSizedImage]) -> str | None:
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
def title_poster(images: SeriesImages) -> str | None:
    tall = images.poster_tall
    if tall and tall[0]:
        return max(tall[0], key=lambda image: image.width).source
    return None


# TODO: Validate
def title_poster_thumbnail(images: SeriesImages) -> str | None:
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


# TODO: Validate
def is_movie(series: SeriesModel) -> bool:
    return "type:movie" in series.keywords
