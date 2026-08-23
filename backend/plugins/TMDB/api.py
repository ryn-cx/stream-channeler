# TODO: Validate
from collections.abc import Callable, Iterator
from datetime import date, timedelta
from functools import cache
from http import HTTPStatus
from typing import Any

import httpx

from app.config import settings


# TODO: Validate
class TMDBHTTPError(Exception):
    # TODO: Validate
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        super().__init__(
            f"Unexpected response status code: {response.status_code}\n{response.text}",
        )


# TODO: Validate
class TMDBInvalidFileError(Exception):
    # TODO: Validate
    def __init__(
        self,
        field: str,
        expected: object = None,
        *,
        response: Any = None,  # noqa: ANN401
    ) -> None:
        self.field = field
        self.expected = expected
        self.response = response
        if expected is None:
            super().__init__(f"Downloaded file has no {field}")
        else:
            super().__init__(f"Downloaded file is not for {field} {expected!r}")


# TMDB is a public API, so a direct client is used rather than the get-around
# proxy. The read access token is stored in the keyring.
# TODO: Validate
@cache
def _client() -> httpx.Client:
    return httpx.Client()


# TODO: Validate
def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = _client().get(
        f"https://api.themoviedb.org/3/{path}",
        params={key: value for key, value in params.items() if value is not None},
        headers={
            "accept": "application/json",
            "Authorization": f"Bearer {settings.TMDB_API_READ_TOKEN}",
        },
    )

    if response.status_code != HTTPStatus.OK:
        raise TMDBHTTPError(response)

    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def _date_chunks(start_date: date, end_date: date) -> Iterator[tuple[date, date]]:
    if start_date >= end_date:
        yield (start_date, start_date)
        return

    window = timedelta(days=14)
    day = timedelta(days=1)
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + window, end_date)
        yield (chunk_start, chunk_end)
        chunk_start = chunk_end + day


# TODO: Validate
def _download_changes(
    start_date: date | None,
    end_date: date | None,
    download: Callable[[str | None, str | None], dict[str, Any]],
) -> dict[str, Any]:
    if start_date is None or end_date is None:
        return download(
            start_date.isoformat() if start_date else None,
            end_date.isoformat() if end_date else None,
        )

    merged: dict[str, list[dict[str, Any]]] = {}
    for chunk_start, chunk_end in _date_chunks(start_date, end_date):
        downloaded = download(chunk_start.isoformat(), chunk_end.isoformat())
        for change in downloaded["changes"]:
            merged.setdefault(change["key"], []).extend(change["items"])
    return {"changes": [{"key": key, "items": items} for key, items in merged.items()]}


# TODO: Validate
def movie_details(
    movie_id: int,
    *,
    append_to_response: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    data = _get(
        f"movie/{movie_id}",
        {
            "append_to_response": append_to_response,
            "language": language or "en-US",
        },
    )
    if data.get("id") != movie_id:
        raise TMDBInvalidFileError(field="movie id", expected=movie_id, response=data)
    return data


# TODO: Validate
def movie_watch_providers(movie_id: int) -> dict[str, Any]:
    data = _get(f"movie/{movie_id}/watch/providers", {})
    if data.get("id") != movie_id:
        raise TMDBInvalidFileError(field="movie id", expected=movie_id, response=data)
    return data


# TODO: Validate
def tv_series_details(
    series_id: int,
    *,
    append_to_response: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    data = _get(
        f"tv/{series_id}",
        {
            "append_to_response": append_to_response,
            "language": language or "en-US",
        },
    )
    if data.get("id") != series_id:
        raise TMDBInvalidFileError(field="series id", expected=series_id, response=data)
    return data


# TODO: Validate
def tv_series_episode_groups(series_id: int) -> dict[str, Any]:
    data = _get(f"tv/{series_id}/episode_groups", {})
    if data.get("id") != series_id:
        raise TMDBInvalidFileError(field="series id", expected=series_id, response=data)
    return data


# TODO: Validate
def tv_series_watch_providers(series_id: int) -> dict[str, Any]:
    data = _get(f"tv/{series_id}/watch/providers", {})
    if data.get("id") != series_id:
        raise TMDBInvalidFileError(field="series id", expected=series_id, response=data)
    return data


# TODO: Validate
def tv_series_changes(
    series_id: int,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
) -> dict[str, Any]:
    # TODO: Validate
    def download(start: str | None, end: str | None) -> dict[str, Any]:
        return _get(
            f"tv/{series_id}/changes",
            {"start_date": start, "end_date": end, "page": page},
        )

    return _download_changes(start_date, end_date, download)


# TODO: Validate
def tv_season_details(
    series_id: int,
    season_number: int,
    *,
    append_to_response: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    data = _get(
        f"tv/{series_id}/season/{season_number}",
        {
            "append_to_response": append_to_response,
            "language": language or "en-US",
        },
    )
    if data.get("season_number") != season_number:
        raise TMDBInvalidFileError(
            field="season number",
            expected=season_number,
            response=data,
        )
    return data


# TODO: Validate
def tv_episode_details(
    series_id: int,
    season_number: int,
    episode_number: int,
    *,
    append_to_response: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    data = _get(
        f"tv/{series_id}/season/{season_number}/episode/{episode_number}",
        {
            "append_to_response": append_to_response,
            "language": language or "en-US",
        },
    )
    if data.get("season_number") != season_number:
        raise TMDBInvalidFileError(
            field="season number",
            expected=season_number,
            response=data,
        )
    if data.get("episode_number") != episode_number:
        raise TMDBInvalidFileError(
            field="episode number",
            expected=episode_number,
            response=data,
        )
    return data


# TODO: Validate
def tv_episode_translations(
    series_id: int,
    season_number: int,
    episode_number: int,
) -> dict[str, Any]:
    return _get(
        f"tv/{series_id}/season/{season_number}/episode/{episode_number}/translations",
        {},
    )


# TODO: Validate
def tv_episode_group_details(tv_episode_group_id: str) -> dict[str, Any]:
    data = _get(f"tv/episode_group/{tv_episode_group_id}", {})
    if data.get("id") != tv_episode_group_id:
        raise TMDBInvalidFileError(
            field="episode group id",
            expected=tv_episode_group_id,
            response=data,
        )
    return data


# TODO: Validate
def search_movie(  # noqa: PLR0913 - Each parameter maps to an API parameter.
    query: str,
    *,
    include_adult: bool = False,
    language: str | None = None,
    primary_release_year: str | None = None,
    region: str | None = None,
    year: str | None = None,
    page: int = 1,
) -> dict[str, Any]:
    data = _get(
        "search/movie",
        {
            "query": query,
            "include_adult": include_adult,
            "language": language or "en-US",
            "primary_release_year": primary_release_year,
            "region": region,
            "year": year,
            "page": page,
        },
    )
    if data.get("page") != page or data.get("results") is None:
        raise TMDBInvalidFileError(field="search page", expected=page, response=data)
    return data


# TODO: Validate
def search_multi(
    query: str,
    *,
    include_adult: bool = False,
    language: str | None = None,
    page: int = 1,
) -> dict[str, Any]:
    data = _get(
        "search/multi",
        {
            "query": query,
            "include_adult": include_adult,
            "language": language,
            "page": page,
        },
    )
    if data.get("page") != page or data.get("results") is None:
        raise TMDBInvalidFileError(field="search page", expected=page, response=data)
    return data


# TODO: Validate
def search_tv(  # noqa: PLR0913 - Each parameter maps to an API parameter.
    query: str,
    *,
    first_air_date_year: int | None = None,
    include_adult: bool = False,
    language: str | None = None,
    year: int | None = None,
    page: int = 1,
) -> dict[str, Any]:
    data = _get(
        "search/tv",
        {
            "query": query,
            "first_air_date_year": first_air_date_year,
            "include_adult": include_adult,
            "language": language or "en-US",
            "year": year,
            "page": page,
        },
    )
    if data.get("page") != page or data.get("results") is None:
        raise TMDBInvalidFileError(field="search page", expected=page, response=data)
    return data
