# TODO: Validate
"""Keys for Crunchyroll's music catalogue.

Music shares a `Plugin` record with the video catalogue, so an artist's keys sit
beside a series' keys and have to be told apart from them. Crunchyroll already
says which of the two an id names in the id itself, so the id is the key, and the
prefix it carries is what a key alone is read by.

A season is the one key with no id behind it, since splitting an artist's releases
into videos and concerts is this plugin's doing rather than something Crunchyroll
numbers, so that key is the listing it stands for. Which artist it belongs to is
the show's to say, and is passed alongside it rather than repeated inside it.
"""

from enum import StrEnum


class MusicCategory(StrEnum):
    """One of the two listings an artist's releases are split into."""

    MUSIC_VIDEO = "musicvideo"
    CONCERT = "concert"


# The prefix Crunchyroll issues ids under, which is what a key is recognised by.
ARTIST_ID_PREFIX = "MA"
SERIES_ID_PREFIX = "G"
CATEGORY_ID_PREFIXES = {
    "MV": MusicCategory.MUSIC_VIDEO,
    "MC": MusicCategory.CONCERT,
}
CATEGORY_ID_PREFIX_LENGTH = 2

# Music is its own `Source` so a channel can take an artist without the video
# catalogue coming with it, and so the two can be scheduled apart. Each source is
# keyed by the name it is shown under, and the plugin owned channel every artist
# is queued into is named after the music source it collects.
VIDEO_SOURCE = "Crunchyroll Videos"
MUSIC_SOURCE = "Crunchyroll Music"
MUSIC_CATEGORY_TO_NAME = {
    MusicCategory.CONCERT: "Concerts",
    MusicCategory.MUSIC_VIDEO: "Music Videos",
}


def is_music_show_key(show_key: str) -> bool:
    """Report whether a `Show` key belongs to an artist rather than a series."""
    return show_key.startswith(ARTIST_ID_PREFIX)


def is_anime_show_key(show_key: str) -> bool:
    """Report whether a `Show` key belongs to a series rather than an artist."""
    return show_key.startswith(SERIES_ID_PREFIX)


def is_music_season_key(season_key: str) -> bool:
    """Report whether a `Season` key belongs to an artist rather than a series."""
    return season_key in set(MusicCategory)


def is_music_episode_key(episode_key: str) -> bool:
    """Report whether an `Episode` key belongs to a music video or a concert."""
    return episode_key.startswith(tuple(CATEGORY_ID_PREFIXES))


def music_episode_category(episode_key: str) -> MusicCategory:
    """Return the listing an episode is a video or a concert of."""
    return CATEGORY_ID_PREFIXES[episode_key[:CATEGORY_ID_PREFIX_LENGTH]]
