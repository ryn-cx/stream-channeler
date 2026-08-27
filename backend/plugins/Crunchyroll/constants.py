# TODO: Validate
from enum import StrEnum

# Music is its own `Source` so a channel can take an artist without the video
# catalogue coming with it, and so the two can be scheduled apart. Each source is
# keyed by the name it is shown under, and the plugin owned channel every artist
# is queued into is named after the music source it collects.
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


# TODO: Validate
def show_is_an_artist(show_key: str) -> bool:
    """Report whether a `Show` key belongs to an artist rather than a series."""
    return show_key.startswith("MA")


# TODO: Validate
def show_is_a_series(show_key: str) -> bool:
    """Report whether a `Show` key belongs to a series rather than an artist."""
    return show_key.startswith("G")


# TODO: Validate
def season_is_music(season_key: str) -> bool:
    """Report whether a `Season` key is for music."""
    return season_key in set(MusicCategory)


# TODO: Validate
def episode_is_music(episode_key: str) -> bool:
    """Report whether an `Episode` key belongs to a music video or a concert."""
    return episode_key.startswith(tuple(CATEGORY_ID_PREFIXES))


# TODO: Validate
def music_episode_category(episode_key: str) -> MusicCategory:
    """Return the listing an episode is a video or a concert of."""
    return CATEGORY_ID_PREFIXES[episode_key[:2]]
