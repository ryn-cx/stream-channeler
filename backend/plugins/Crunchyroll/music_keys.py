# TODO: Validate
"""Keys for Crunchyroll's music catalogue.

Music shares a `Plugin` record with the video catalogue, so an artist's keys are
prefixed with what they are to keep them apart from a series' keys and to let a
key alone say which file it is read from.
"""

from enum import StrEnum
from typing import NamedTuple


class MusicCategory(StrEnum):
    """One of the two listings an artist's releases are split into."""

    MUSIC_VIDEO = "musicvideo"
    CONCERT = "concert"


ARTIST_PREFIX = "artist"

# Music is its own `Source` so a channel can take an artist without the video
# catalogue coming with it, and so the two can be scheduled apart.
VIDEO_SOURCE_KEY = "Crunchyroll"
VIDEO_SOURCE_NAME = "Crunchyroll"
MUSIC_SOURCE_KEY = "CrunchyrollMusic"
MUSIC_SOURCE_NAME = "Crunchyroll Music"

# Every artist Crunchyroll releases music for is queued into one plugin owned
# channel, since their own site gives no way to browse the catalogue.
MUSIC_CHANNEL_NAME = "Crunchyroll Music"

# An artist's videos and concerts are two separate listings, so each becomes a
# season of its own rather than one flat list of everything they released.
CATEGORY_NAMES = {
    MusicCategory.MUSIC_VIDEO: "Music Videos",
    MusicCategory.CONCERT: "Concerts",
}


class MusicSeasonKey(NamedTuple):
    """The parts of a music `Season` key."""

    artist_id: str
    category: MusicCategory


class MusicEpisodeKey(NamedTuple):
    """The parts of a music `Episode` key."""

    category: MusicCategory
    video_id: str


def artist_show_key(artist_id: str) -> str:
    """Return the `Show` key for an artist."""
    return f"{ARTIST_PREFIX}/{artist_id}"


def music_season_key(artist_id: str, category: MusicCategory) -> str:
    """Return the `Season` key for one of an artist's categories."""
    return f"{ARTIST_PREFIX}/{artist_id}/{category}"


def music_episode_key(category: MusicCategory, video_id: str) -> str:
    """Return the `Episode` key for a music video or a concert."""
    return f"{category}/{video_id}"


def is_artist_show_key(show_key: str) -> bool:
    """Report whether a `Show` key belongs to an artist rather than a series."""
    return show_key.startswith(f"{ARTIST_PREFIX}/")


def is_music_season_key(season_key: str) -> bool:
    """Report whether a `Season` key belongs to an artist rather than a series."""
    return season_key.startswith(f"{ARTIST_PREFIX}/")


def is_music_episode_key(episode_key: str) -> bool:
    """Report whether an `Episode` key belongs to a music video or a concert."""
    return episode_key.startswith(tuple(f"{category}/" for category in MusicCategory))


def parse_artist_show_key(show_key: str) -> str:
    """Return the artist id a `Show` key is built from."""
    return show_key.split("/", 1)[1]


def parse_music_season_key(season_key: str) -> MusicSeasonKey:
    """Return the parts a music `Season` key is built from.

    A season is reached from its key alone, without the show's, so the key
    carries the artist as well as the category.
    """
    _, artist_id, category = season_key.split("/")
    return MusicSeasonKey(artist_id, MusicCategory(category))


def parse_music_episode_key(episode_key: str) -> MusicEpisodeKey:
    """Return the parts a music `Episode` key is built from."""
    category, video_id = episode_key.split("/", 1)
    return MusicEpisodeKey(MusicCategory(category), video_id)
