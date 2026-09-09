# TODO: Validate
from enum import StrEnum

VIDEO_SOURCE = "Crunchyroll"
MUSIC_SOURCE = "Crunchyroll Music"


# TODO: Validate
class CrunchyrollMusicCategory(StrEnum):
    MUSIC_VIDEO = "musicvideo"
    CONCERT = "concert"


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
