# TODO: Validate
from collections.abc import Iterator, Sequence
from http import HTTPStatus
from itertools import batched
from json import JSONDecodeError
from time import sleep
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx

from app.config import settings
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class YouTubeHTTPError(Exception):
    # TODO: Validate
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        super().__init__(
            f"Unexpected response status code: {response.status_code}\n{response.text}",
        )


# TODO: Validate
class YouTubeAPIError(Exception):
    # TODO: Validate
    def __init__(self, error: dict[str, Any], response: dict[str, Any]) -> None:
        self.error = error
        self.code = error["code"]
        self.response = response
        super().__init__(f"{self.code}: {error['message']}")


# TODO: Validate
class YouTubeNotFoundError(YouTubeAPIError):
    pass


# TODO: Validate
def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = get_around_client().get(
        f"https://www.googleapis.com/youtube/v3/{path}",
        params={**params, "key": settings.YOUTUBE_API_KEY},
    )

    try:
        body: dict[str, Any] = response.json()
    except JSONDecodeError as error:
        raise YouTubeHTTPError(response) from error

    if error_object := body.get("error"):
        if error_object["code"] == HTTPStatus.NOT_FOUND:
            raise YouTubeNotFoundError(error_object, body)
        raise YouTubeAPIError(error_object, body)

    if response.status_code != HTTPStatus.OK:
        raise YouTubeHTTPError(response)

    return body


# TODO: Validate
def channels_list(
    *,
    channel_id: str | None = None,
    channel_handle: str | None = None,
    channel_username: str | None = None,
) -> dict[str, Any]:
    given = {
        name: value
        for name, value in (
            ("id", channel_id),
            ("forHandle", channel_handle),
            ("forUsername", channel_username),
        )
        if value is not None
    }
    if len(given) != 1:
        msg = "Invalid number of arguments."
        raise ValueError(msg)

    return _get(
        "channels",
        {
            **given,
            "part": (
                "brandingSettings,contentDetails,contentOwnerDetails,id,"
                "localizations,snippet,statistics,status,topicDetails"
            ),
        },
    )


# TODO: Validate
def playlists_list(
    *,
    playlist_ids: str | Sequence[str] | None = None,
    channel_id: str | None = None,
    page_token: str | None = None,
) -> dict[str, Any]:
    identifiers = [playlist_ids] if isinstance(playlist_ids, str) else playlist_ids
    given = {
        name: value
        for name, value in (
            ("id", ",".join(identifiers) if identifiers is not None else None),
            ("channelId", channel_id),
        )
        if value is not None
    }
    if len(given) != 1:
        msg = "Invalid number of arguments."
        raise ValueError(msg)

    params: dict[str, Any] = {
        **given,
        "part": "contentDetails,id,localizations,player,snippet,status",
        "maxResults": 50,
    }
    if page_token is not None:
        params["pageToken"] = page_token

    return _get("playlists", params)


# TODO: Validate
def playlist_items_list(
    playlist_id: str,
    page_token: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "part": "contentDetails,id,snippet,status",
        "playlistId": playlist_id,
        "maxResults": 50,
    }
    if page_token is not None:
        params["pageToken"] = page_token

    return _get("playlistItems", params)


# TODO: Validate
def videos_list(video_ids: str | Sequence[str]) -> dict[str, Any]:
    identifiers = [video_ids] if isinstance(video_ids, str) else list(video_ids)
    return _get(
        "videos",
        {
            "part": (
                "contentDetails,id,liveStreamingDetails,localizations,"
                "paidProductPlacementDetails,player,recordingDetails,snippet,"
                "statistics,status,topicDetails"
            ),
            "id": ",".join(identifiers),
        },
    )


# TODO: Validate
def videos_list_batched(video_ids: Sequence[str]) -> Iterator[dict[str, Any]]:
    for batch in batched(video_ids, 50, strict=False):
        yield videos_list(batch)


# TODO: Validate
def feed(*, channel_id: str | None = None, playlist_id: str | None = None) -> str:
    given = {
        name: value
        for name, value in (
            ("channel_id", channel_id),
            ("playlist_id", playlist_id),
        )
        if value is not None
    }
    if len(given) != 1:
        msg = "Invalid number of arguments."
        raise ValueError(msg)

    response = get_around_client().get(
        "https://www.youtube.com/feeds/videos.xml",
        params=given,
    )
    if response.status_code != HTTPStatus.OK:
        raise YouTubeHTTPError(response)
    return response.text


# TODO: Validate
def browse(asked: dict[str, Any]) -> dict[str, Any]:
    response = get_around_client().post(
        "https://www.youtube.com/youtubei/v1/browse",
        json={
            **asked,
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240401.00.00",
                },
            },
        },
        headers={"Content-Type": "application/json"},
    )

    sleep(1)

    if response.status_code != HTTPStatus.OK:
        raise YouTubeHTTPError(response)

    browsed: dict[str, Any] = response.json()
    return browsed


# TODO: Validate
def find(node: Any, key: str) -> Iterator[Any]:  # noqa: ANN401 - Browse data is any JSON.
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                yield value
            yield from find(value, key)
    elif isinstance(node, list):
        for value in node:
            yield from find(value, key)


# TODO: Validate
def read_text(node: dict[str, Any]) -> str:
    if "simpleText" in node:
        simple: str = node["simpleText"]
        return simple
    return "".join(run["text"] for run in node.get("runs", ()))


# TODO: Validate
def read_continuation(browsed: dict[str, Any]) -> str | None:
    return next(
        (
            renderer["continuationEndpoint"]["continuationCommand"]["token"]
            for renderer in find(browsed, "continuationItemRenderer")
            if "continuationEndpoint" in renderer
        ),
        None,
    )


# TODO: Validate
def read_seasons(
    browsed: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], int | None]:
    menu = next(find(browsed, "sortFilterSubMenuRenderer"), None)
    if menu is None:
        return {}, None

    seasons: dict[int, dict[str, Any]] = {}
    open_season: int | None = None
    for item in menu.get("subMenuItems", ()):
        endpoint = item.get("navigationEndpoint")
        if endpoint is None:
            continue
        path = endpoint["commandMetadata"]["webCommandMetadata"]["url"]
        numbers = parse_qs(urlsplit(path).query).get("season", ())
        if not numbers or not numbers[0].isdigit():
            continue
        number = int(numbers[0])
        seasons[number] = endpoint["browseEndpoint"]
        if item.get("selected"):
            open_season = number
    return seasons, open_season


# TODO: Validate
def _pages_to_the_end(opened: dict[str, Any]) -> list[dict[str, Any]]:
    pages = [opened]
    while (continuation := read_continuation(pages[-1])) is not None:
        pages.append(browse({"continuation": continuation}))
    return pages


# TODO: Validate
def show_pages(playlist_id: str) -> list[dict[str, Any]]:
    browse_id = playlist_id if playlist_id.startswith("SC") else f"VL{playlist_id}"
    opened = browse({"browseId": browse_id})
    seasons, open_season = read_seasons(opened)

    pages = _pages_to_the_end(opened)
    for number, endpoint in sorted(seasons.items()):
        if number == open_season:
            continue
        asked: dict[str, Any] = {"browseId": endpoint["browseId"]}
        if endpoint.get("params") is not None:
            asked["params"] = endpoint["params"]
        pages.extend(_pages_to_the_end(browse(asked)))
    return pages


# TODO: Validate
def music_playlist(playlist_id: str) -> dict[str, Any]:
    return browse({"browseId": f"VL{playlist_id}"})


# TODO: Validate
def _topic_continuation(browsed: dict[str, Any]) -> str | None:
    shelf = next(find(browsed, "shelfRenderer"), None)
    if shelf is None:
        return read_continuation(browsed)
    token: str | None = next(find(shelf["endpoint"], "token"), None)
    return token


# TODO: Validate
def topic_pages(channel_id: str) -> list[dict[str, Any]]:
    pages = [browse({"browseId": channel_id})]
    while (continuation := _topic_continuation(pages[-1])) is not None:
        pages.append(browse({"continuation": continuation}))
    return pages
