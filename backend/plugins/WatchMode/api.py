# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from http import HTTPStatus
from typing import Any

import httpx

from app.config import settings
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class WatchModeHTTPError(Exception):
    # TODO: Validate
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        super().__init__(
            f"Unexpected response status code: {response.status_code}\n{response.text}",
        )


# TODO: Validate
class WatchModeUnauthorizedError(WatchModeHTTPError):
    pass


# TODO: Validate
class WatchModeResourceNotFoundError(WatchModeHTTPError):
    pass


# TODO: Validate
class TitleIdError(ValueError):
    # TODO: Validate
    def __init__(self, title_ids: list[str]) -> None:
        self.inputs_with_values = title_ids
        if title_ids:
            super().__init__(f"Only one title id may be given, got: {title_ids}")
        else:
            super().__init__("A title id is required")


# TODO: Validate
def _prefixed(value: str | int, prefix: str) -> str:
    value = str(value).strip()
    if value.startswith(prefix):
        return value
    return f"{prefix}{value}"


# TODO: Validate
def extract_title_id(
    title_id: str | int | None = None,
    *,
    watchmode_id: str | int | None = None,
    imdb_id: str | None = None,
    tmdb_movie_id: str | int | None = None,
    tmdb_tv_id: str | int | None = None,
) -> str:
    inputs: dict[str, str | int | None] = {
        "title_id": title_id,
        "watchmode_id": watchmode_id,
        "imdb_id": imdb_id,
        "tmdb_movie_id": tmdb_movie_id,
        "tmdb_tv_id": tmdb_tv_id,
    }
    title_ids = [name for name, value in inputs.items() if value is not None]
    if len(title_ids) != 1:
        raise TitleIdError(title_ids)

    if title_id is not None:
        return str(title_id).strip()
    if watchmode_id is not None:
        return str(watchmode_id).strip()
    if imdb_id is not None:
        return _prefixed(imdb_id, "tt")
    if tmdb_movie_id is not None:
        return _prefixed(tmdb_movie_id, "movie-")
    if tmdb_tv_id is not None:
        return _prefixed(tmdb_tv_id, "tv-")
    raise TitleIdError(title_ids)


# TODO: Validate
def _get(endpoint: str, params: dict[str, Any]) -> Any:  # noqa: ANN401
    response = get_around_client().get(
        f"https://api.watchmode.com/v1/{endpoint}",
        params={key: value for key, value in params.items() if value is not None},
        headers={
            "accept": "application/json",
            "X-API-Key": settings.WATCHMODE_API_KEY,
        },
    )

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise WatchModeUnauthorizedError(response)
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise WatchModeResourceNotFoundError(response)
    if response.status_code != HTTPStatus.OK:
        raise WatchModeHTTPError(response)

    return response.json()


# TODO: Validate
def title_sources(
    title_id: str | int,
    *,
    regions: str | Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    if regions is not None and not isinstance(regions, str):
        regions = ",".join(regions)

    sources: list[dict[str, Any]] = _get(
        f"title/{extract_title_id(title_id)}/sources/",
        {"regions": regions},
    )
    return sources
