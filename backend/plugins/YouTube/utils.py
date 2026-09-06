# TODO: Validate
"""What every other part of the plugin reads a YouTube title by."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

from not_yt_dlapi.exceptions import APIError


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://youtube.com/{path.lstrip('/')}"


# TODO: Validate
def channel_url(channel_key: str) -> str:
    return build_url(f"channel/{channel_key}")


# TODO: Validate
def video_url(video_key: str) -> str:
    return build_url(f"watch?v={video_key}")


# TODO: Validate
def playlist_url(playlist_key: str) -> str:
    return build_url(f"playlist?list={playlist_key}")


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"show/{title_key}")


# TODO: Validate
def title_season_url(title_key: str, season_number: str) -> str:
    return build_url(f"show/{title_key}?season={season_number}")


# TODO: Validate
def search_url(query: str) -> str:
    return build_url(f"results?search_query={quote(query)}")


# TODO: Validate
def is_an_album(key: str) -> bool:
    return key.startswith("OLAK5uy_")


# TODO: Validate
def is_user_playlist(key: str) -> bool:
    return key.startswith("PL")


# TODO: Validate
def is_video_key(key: str) -> bool:
    """Return whether a  is for a video.

    Title.key and Season.key is a video key if it is a free movie."""
    # Videos are always 11 characters long and channels/playlists are never 11
    # characters long.
    return len(key) == 11  # noqa: PLR2004


# TODO: Validate
def is_title_key(key: str) -> bool:
    """Report whether a key belongs to a title page."""
    return key.startswith("SC")


# TODO: Validate
def is_channel_key(key: str) -> bool:
    """Report whether a key belongs to a channel rather than to what one holds."""
    return not (
        is_video_key(key)
        or is_title_key(key)
        or is_an_album(key)
        or is_user_playlist(key)
    )


# TODO: Validate
def is_channel_uploads_playlist_key(key: str) -> bool:
    return key.startswith("UU")


# TODO: Validate
def is_regular_playlist(key: str) -> bool:
    return key.startswith("PL") or is_channel_uploads_playlist_key(key)


# TODO: Validate
def channel_key_from_uploads_playlist_key(key: str) -> str:
    return key[:1] + "C" + key[2:]


# TODO: Validate
def channel_uploads_playlist_key(title_key: str) -> str:
    """Return the playlist ID for the channel's uploads."""
    return title_key[:1] + "U" + title_key[2:]


# TODO: Validate
def title_season_key(title_key: str, season_number: str) -> str:
    """Return the season key for one season of a title."""
    return f"{title_key}/{season_number}"


# TODO: Validate
def is_title_season_key(key: str) -> bool:
    """Report whether a key belongs to one season of a title."""
    return is_title_key(key) and "/" in key


# TODO: Validate
def split_title_season_key(season_key: str) -> tuple[str, str]:
    """Split a season key back into its title key and season number."""
    title_key, _, season_number = season_key.partition("/")
    return title_key, season_number


# TODO: Validate
def get_first_item[T](items: Sequence[T] | None) -> T:
    if not items:
        msg = "Expected at least one item, got none"
        raise ValueError(msg)
    return items[0]


# TODO: Validate
def is_free_movies_channel(channel_key: str) -> bool:
    """Report whether a channel is the one YouTube's free catalogue is published on.

    Everything YouTube serves free with ads is owned by this one channel, and a
    title that has to be bought or rented is owned by a channel generated for
    that title alone, so who owns a video is what says which of the two it is.
    """
    return channel_key == "UCuVPpxrm2VAgpH3Ktln4HXg"


# TODO: Validate
def is_quota_error(error: BaseException) -> bool:
    """Report whether `error` is the YouTube API refusing calls until quota resets."""
    if not isinstance(error, APIError):
        return False
    errors = error.error.get("errors", [])
    return any(
        item.get("reason") in frozenset({"dailyLimitExceeded", "quotaExceeded"})
        for item in errors
    )


# TODO: Validate
def video_is_valid(video_title: str) -> bool:
    """Check if a video is valid for importing."""
    return video_title not in ("Deleted video", "Private video")


# TODO: Validate
def best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
    # It sounds wrong but standard is a higher resolution than high.
    for quality in ("maxres", "standard", "high", "medium", "default"):
        if thumb := getattr(thumbnails, quality, None):
            url: str = thumb.url
            return url
    return None


# TODO: Validate
def thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
    for quality in ("standard", "high", "medium", "default", "maxres"):
        if thumb := getattr(thumbnails, quality, None):
            url: str = thumb.url
            return url
    return None
