# TODO: Validate
from __future__ import annotations

import json
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from app.utils import tz_datetime
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class CrunchyrollError(Exception):
    response: str | dict[str, Any] | None = None


# TODO: Validate
class HTTPError(CrunchyrollError):
    # TODO: Validate
    def __init__(
        self,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(f"Unexpected response status code: {status_code}")


# TODO: Validate
class ResourceNotFoundError(HTTPError):
    pass


# TODO: Validate
class EpisodeNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        object_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.object_id = object_id
        super().__init__(status_code, response)


# TODO: Validate
class SeriesNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        series_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.series_id = series_id
        super().__init__(status_code, response)


# TODO: Validate
class SeasonNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        season_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.season_id = season_id
        super().__init__(status_code, response)


# TODO: Validate
class MusicVideoNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        music_video_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.music_video_id = music_video_id
        super().__init__(status_code, response)


# TODO: Validate
class ConcertNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        concert_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.concert_id = concert_id
        super().__init__(status_code, response)


# TODO: Validate
class ArtistNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        artist_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.artist_id = artist_id
        super().__init__(status_code, response)


# TODO: Validate
class StartOutOfRangeError(CrunchyrollError, ValueError):
    # TODO: Validate
    def __init__(self, start: int, total: int, response: dict[str, Any]) -> None:
        self.start = start
        self.total = total
        self.response = response
        super().__init__(f"Requested start {start} exceeds total {total}")


_access_token: str | None = None
_access_token_expires_at: datetime | None = None
_device_id = uuid4().hex


# TODO: Validate
def _download_access_token() -> str:
    global _access_token, _access_token_expires_at  # noqa: PLW0603

    response = get_around_client().post(
        "https://beta-api.crunchyroll.com/auth/v1/token",
        data={
            "device_id": _device_id,
            "device_type": "Microsoft Edge on Windows",
            "grant_type": "client_id",
        },
        headers={"Authorization": "Basic bm9haWhkZXZtXzZpeWcwYThsMHE6"},
    )
    if response.status_code != HTTPStatus.OK:
        raise HTTPError(response.status_code, response.text)

    parsed = response.json()
    token: str = parsed["access_token"]
    _access_token = token
    _access_token_expires_at = tz_datetime.now() + timedelta(
        seconds=parsed["expires_in"],
    )
    return token


# TODO: Validate
def _current_access_token() -> str:
    if (
        _access_token is None
        or _access_token_expires_at is None
        or _access_token_expires_at < tz_datetime.now()
    ):
        return _download_access_token()
    return _access_token


# TODO: Validate
def _get(
    endpoint: str,
    params: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    response = get_around_client().get(
        f"https://beta-api.crunchyroll.com/{endpoint}",
        params=params,
        headers={**headers, "authorization": f"Bearer {_current_access_token()}"},
    )

    if response.status_code != HTTPStatus.OK:
        try:
            code = json.loads(response.text).get("code")
        except ValueError, AttributeError:
            code = None
        if isinstance(code, str) and code.endswith(".resource_not_found"):
            raise ResourceNotFoundError(response.status_code, response.text)
        raise HTTPError(response.status_code, response.text)

    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def series(series_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/cms/series/{series_id}",
            {"locale": locale},
            {"referer": f"https://www.crunchyroll.com/series/{series_id}"},
        )
    except ResourceNotFoundError as error:
        raise SeriesNotFoundError(
            series_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def seasons(series_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        response = _get(
            f"content/v2/cms/series/{series_id}/seasons",
            {"locale": locale, "force_locale": None},
            {"referer": f"https://www.crunchyroll.com/series/{series_id}"},
        )
    except ResourceNotFoundError as error:
        raise SeriesNotFoundError(
            series_id,
            error.status_code,
            error.response,
        ) from error

    if not response.get("data"):
        raise SeriesNotFoundError(series_id, HTTPStatus.OK, response)
    return response


# TODO: Validate
def season_episodes(season_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        response = _get(
            f"content/v2/cms/seasons/{season_id}/episodes",
            {"locale": locale},
            {"referer": f"https://www.crunchyroll.com/series/{season_id}"},
        )
    except ResourceNotFoundError as error:
        raise SeasonNotFoundError(
            season_id,
            error.status_code,
            error.response,
        ) from error

    if not response.get("data"):
        raise SeasonNotFoundError(season_id, HTTPStatus.OK, response)
    return response


# TODO: Validate
def objects(object_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/cms/objects/{object_id}",
            {"ratings": True, "locale": locale},
            {"referer": f"https://www.crunchyroll.com/watch/{object_id}"},
        )
    except ResourceNotFoundError as error:
        raise EpisodeNotFoundError(
            object_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def search(
    query: str,
    *,
    number_of_results: int = 6,
    search_type: str = "music,series,episode,movie_listing,top_results",
    ratings: bool = True,
    locale: str = "en-US",
) -> dict[str, Any]:
    return _get(
        "content/v2/discover/search",
        {
            "q": query,
            "n": number_of_results,
            "type": search_type,
            "ratings": str(ratings).lower(),
            "locale": locale,
        },
        {"referer": "https://www.crunchyroll.com/search"},
    )


# TODO: Validate
def artist(artist_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/music/artists/{artist_id}",
            {"locale": locale},
            {"referer": f"https://www.crunchyroll.com/artist/{artist_id}"},
        )
    except ResourceNotFoundError as error:
        raise ArtistNotFoundError(
            artist_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def artist_music_videos(artist_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/music/artists/{artist_id}/music_videos",
            {"locale": locale},
            {"referer": f"https://www.crunchyroll.com/artist/{artist_id}"},
        )
    except ResourceNotFoundError as error:
        raise ArtistNotFoundError(
            artist_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def artist_concerts(artist_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/music/artists/{artist_id}/concerts",
            {"locale": locale},
            {"referer": f"https://www.crunchyroll.com/artist/{artist_id}"},
        )
    except ResourceNotFoundError as error:
        raise ArtistNotFoundError(
            artist_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def music_video(music_video_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/music/music_videos/{music_video_id}",
            {"locale": locale},
            {
                "referer": (
                    f"https://www.crunchyroll.com/watch/musicvideo/{music_video_id}"
                ),
            },
        )
    except ResourceNotFoundError as error:
        raise MusicVideoNotFoundError(
            music_video_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def concert(concert_id: str, *, locale: str = "en-US") -> dict[str, Any]:
    try:
        return _get(
            f"content/v2/music/concerts/{concert_id}",
            {"locale": locale},
            {"referer": f"https://www.crunchyroll.com/watch/concert/{concert_id}"},
        )
    except ResourceNotFoundError as error:
        raise ConcertNotFoundError(
            concert_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def browse_series(
    *,
    start: int = 0,
    number_of_results: int = 36,
    sort_by: str = "newly_added",
    ratings: str = "true",
    locale: str = "en-US",
) -> dict[str, Any]:
    params: dict[str, str | int] = {
        "n": number_of_results,
        "sort_by": sort_by,
        "ratings": ratings,
        "locale": locale,
    }
    if start:
        params["start"] = start

    response = _get(
        "content/v2/discover/browse",
        params,
        {"referer": "https://www.crunchyroll.com/videos/new"},
    )
    if start and start > response["total"]:
        raise StartOutOfRangeError(start, response["total"], response)
    return response


# TODO: Validate
def browse_series_until_datetime(
    end_datetime: datetime | None = None,
    *,
    number_of_results: int = 36,
    sort_by: str = "newly_added",
    ratings: str = "true",
    locale: str = "en-US",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    start = 0
    end_datetime = end_datetime or datetime.now().astimezone()
    while True:
        page = browse_series(
            start=start,
            number_of_results=number_of_results,
            sort_by=sort_by,
            ratings=ratings,
            locale=locale,
        )
        results.append(page)
        start += number_of_results
        last_public = datetime.fromisoformat(page["data"][-1]["last_public"])
        if last_public < end_datetime or start >= page["total"]:
            return results


# TODO: Validate
def browse_music(
    *,
    start: int = 0,
    number_of_results: int = 36,
    locale: str = "en-US",
) -> dict[str, Any]:
    params: dict[str, str | int] = {"n": number_of_results, "locale": locale}
    if start:
        params["start"] = start

    response = _get(
        "content/v2/music/browse",
        params,
        {"referer": "https://www.crunchyroll.com/music"},
    )
    if start and start > response["total"]:
        raise StartOutOfRangeError(start, response["total"], response)
    return response


# TODO: Validate
def browse_music_all(
    *,
    number_of_results: int = 36,
    locale: str = "en-US",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    start = 0
    while True:
        page = browse_music(
            start=start,
            number_of_results=number_of_results,
            locale=locale,
        )
        results.append(page)
        start += number_of_results
        if start >= page["total"]:
            return results


# TODO: Validate
def extract_data(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [datum for page in pages for datum in page["data"]]
