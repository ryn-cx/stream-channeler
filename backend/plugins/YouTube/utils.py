# TODO: Validate
"""What every other part of the plugin reads a YouTube title by."""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from typing import Any

from loguru import logger
from not_yt_dlapi.exceptions import APIError

from plugins.YouTube.files import (
    # Browse,
    ChannelByChannelId,
    Topic,
    Videos,
    not_yt_dlapi,
)


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


# # TODO: Validate
# def title_url(title_key: str) -> str:
#     return build_url(f"show/{title_key}")


# # TODO: Validate
# def title_season_url(title_key: str, season_number: str) -> str:
#     return build_url(f"show/{title_key}?season={season_number}")


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


# # TODO: Validate
# def is_regular_playlist(key: str) -> bool:
#     return key.startswith("PL") or is_channel_uploads_playlist_key(key)


# TODO: Validate
def channel_key_from_uploads_playlist_key(key: str) -> str:
    return key[:1] + "C" + key[2:]


# TODO: Validate
def channel_uploads_playlist_key(title_key: str) -> str:
    """Return the playlist ID for the channel's uploads."""
    return title_key[:1] + "U" + title_key[2:]


# # TODO: Validate
# def title_season_key(title_key: str, season_number: str) -> str:
#     """Return the season key for one season of a title."""
#     return f"{title_key}/{season_number}"


# # TODO: Validate
# def is_title_season_key(key: str) -> bool:
#     """Report whether a key belongs to one season of a title."""
#     return is_title_key(key) and "/" in key


# # TODO: Validate
# def split_title_season_key(season_key: str) -> tuple[str, str]:
#     """Split a season key back into its title key and season number."""
#     title_key, _, season_number = season_key.partition("/")
#     return title_key, season_number


# TODO: Validate
def get_first_item[T](items: Sequence[T] | None) -> T:
    if not items:
        msg = "Expected at least one item, got none"
        raise ValueError(msg)
    return items[0]


# # TODO: Validate
# def is_free_movies_channel(channel_key: str) -> bool:
#     """Report whether a channel is the one YouTube's free catalogue is published on.

#     Everything YouTube serves free with ads is owned by this one channel, and a
#     title that has to be bought or rented is owned by a channel generated for
#     that title alone, so who owns a video is what says which of the two it is.
#     """
#     return channel_key == "UCuVPpxrm2VAgpH3Ktln4HXg"


# TODO: Validate
def is_quota_error(error: BaseException) -> bool:
    if not isinstance(error, APIError):
        return False
    return any(item["reason"] == "quotaExceeded" for item in error.error["errors"])


# TODO: Validate
def video_is_valid(video_title: str) -> bool:
    """Check if a video is valid for importing."""
    return video_title not in ("Deleted video", "Private video")


# TODO: Validate
def image_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
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


# TODO: Validate
def is_topic_channel(channel_file: ChannelByChannelId) -> bool:
    """Report whether a channel key belongs to a musician's Topic channel.

    Only the channel says so, and this reads what has been downloaded rather
    than downloading it, so a channel that has not been read yet is answered
    for as the plain channel it is taken for until it has been.
    """
    if not is_channel_key(channel_file.unique_identifier):
        return False

    if channel_file.is_outdated() or not channel_file.record_content:
        return False
    items = channel_file.parsed().items
    if not items:
        return False
    return items[0].snippet.title.endswith(" - Topic")


# # TODO: Validate
# def is_movies_channel(channel_file: ChannelByChannelId) -> bool:
#     if not is_channel_key(channel_file.unique_identifier):
#         return False

#     if channel_file.is_outdated() or not channel_file.record_content:
#         return False
#     items = channel_file.parsed().items
#     if not items:
#         return False
#     return items[0].snippet.title == "YouTube Movies"


# # TODO: Validate
# def is_usa_video(videos_file: Videos) -> bool:
#     # A video that has not been read yet is taken to be one, since what says
#     # otherwise is the video itself and reading it is what this decides.
#     if videos_file.is_outdated() or not videos_file.record_content:
#         return True

#     items = videos_file.parsed().items
#     if not items:
#         return False
#     restriction = items[0].content_details.region_restriction
#     if restriction is None or restriction.allowed is None:
#         return False
#     return "US" in restriction.allowed


# TODO: Validate
def topic_release_keys_from_file(topic_file: Topic) -> list[str]:
    """Return the playlist key of every release a Topic channel lists."""
    return [
        release_key
        for release_key in topic_file.release_keys()
        if is_an_album(release_key)
    ]


# # TODO: Validate
# def title_season_numbers_from_file(show_file: Browse) -> list[str]:
#     return [str(number) for number in show_file.season_numbers()]


# TODO: Validate
def batch_download_missing_videos(videos_files: Sequence[Videos]) -> None:
    outdated_files = [
        videos_file for videos_file in videos_files if videos_file.is_outdated()
    ]
    if not outdated_files:
        return

    outdated_ids = [videos_file.unique_identifier for videos_file in outdated_files]
    logger.info(f"Batch downloading {len(outdated_ids)} YouTube videos")
    start = time.monotonic()
    responses = not_yt_dlapi().videos.download_all(outdated_ids)
    elapsed_time = time.monotonic() - start
    logger.info(
        f"Batch downloaded {len(outdated_ids)} YouTube videos in {elapsed_time:.2f}s",
    )

    # A batch answers for fifty videos at once and every video is stored in a
    # file of its own, so each item is written out as the response it would
    # have arrived in had it been asked for on its own.
    responses_by_id: dict[str, str] = {}
    for response in responses:
        page: dict[str, Any] = json.loads(response)
        for item in page["items"]:
            responses_by_id[item["id"]] = json.dumps({**page, "items": [item]})
    for videos_file in outdated_files:
        # write is called directly because of the way the files are batch
        # downloaded.
        videos_file.write(responses_by_id[videos_file.unique_identifier])
