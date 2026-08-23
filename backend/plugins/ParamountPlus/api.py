# TODO: Validate
import json
import re
from http import HTTPStatus
from typing import Any

import httpx

from plugins.utils.get_around_client import get_around_client

_LD_JSON_REGEX = re.compile(
    r'<script type="application/ld\+json">(?P<json>.*?)</script>',
    re.DOTALL,
)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


# TODO: Validate
class ParamountPlusError(Exception):
    response: str | dict[str, Any] | None = None


# TODO: Validate
class ParamountPlusHTTPError(ParamountPlusError):
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
class ResourceNotFoundError(ParamountPlusHTTPError):
    pass


# TODO: Validate
class ShowNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        show: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.show = show
        super().__init__(status_code, response)


# TODO: Validate
class SeasonNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        show: str,
        season: int,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.show = show
        self.season = season
        super().__init__(status_code, response)


# TODO: Validate
class MovieNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        movie_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.movie_id = movie_id
        super().__init__(status_code, response)


# TODO: Validate
class ExtractionError(ParamountPlusError):
    pass


# TODO: Validate
def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise ResourceNotFoundError(response.status_code, response.text)
    raise ParamountPlusHTTPError(response.status_code, response.text)


# TODO: Validate
def _get_json(
    url: str,
    *,
    referer: str,
) -> dict[str, Any]:
    response = get_around_client().get(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        },
        follow_redirects=True,
    )
    if response.status_code != HTTPStatus.OK:
        _raise_for_status(response)
    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def _get_html(url: str, *, referer: str) -> str:
    response = get_around_client().get(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0, i",
        },
        follow_redirects=True,
    )
    if response.status_code != HTTPStatus.OK:
        _raise_for_status(response)
    return response.text


# TODO: Validate
def _extract_ld_json(html: str, schema_type: str) -> dict[str, Any]:
    for match in _LD_JSON_REGEX.finditer(html):
        block: dict[str, Any] = json.loads(match.group("json"))
        if block.get("@type") == schema_type:
            return block
    msg = f"No ld+json block with @type {schema_type!r} found in the page HTML"
    raise ExtractionError(msg)


# TODO: Validate
def episodes(
    show_id: str,
    *,
    season_number: int,
    page: int = 0,
    size: int = 18,
) -> dict[str, Any]:
    url = (
        f"https://www.paramountplus.com/shows/{show_id}/xhr/episodes"
        f"/page/{page}/size/{size}/xs/0/season/{season_number}/"
    )
    try:
        response = _get_json(
            url,
            referer=f"https://www.paramountplus.com/shows/{show_id}/",
        )
    except ResourceNotFoundError as error:
        raise ShowNotFoundError(
            show_id,
            error.status_code,
            error.response,
        ) from error

    if not response["result"]["data"]:
        raise SeasonNotFoundError(show_id, season_number, HTTPStatus.OK, response)
    return response


# TODO: Validate
def movie(movie_id: str) -> dict[str, Any]:
    url = f"https://www.paramountplus.com/movies/video/{movie_id}/"
    try:
        html = _get_html(url, referer="https://www.paramountplus.com/movies/")
    except ResourceNotFoundError as error:
        raise MovieNotFoundError(
            movie_id,
            error.status_code,
            error.response,
        ) from error
    return _extract_ld_json(html, "Movie")
