# TODO: Validate
import json
import re
from http import HTTPStatus
from typing import Any

from plugins.utils.get_around_client import get_around_client

_NEXT_DATA_REGEX = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(?P<json>.*?)</script>',
    re.DOTALL,
)


# TODO: Validate
class HBOMaxError(Exception):
    pass


# TODO: Validate
class HBOMaxHTTPError(HBOMaxError):
    # TODO: Validate
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Unexpected response status code: {status_code}\n{body}")


# TODO: Validate
class HBOMaxExtractionError(HBOMaxError):
    pass


# TODO: Validate
def extract_next_data(html: str) -> dict[str, Any]:
    match = _NEXT_DATA_REGEX.search(html)
    if match is None:
        msg = "Could not find __NEXT_DATA__ script tag in the page HTML"
        raise HBOMaxExtractionError(msg)
    parsed: dict[str, Any] = json.loads(match.group("json"))
    return parsed


# TODO: Validate
def _get(url: str) -> dict[str, Any]:
    response = get_around_client().get(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.hbomax.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0, i",
        },
        follow_redirects=True,
    )
    if response.status_code != HTTPStatus.OK:
        raise HBOMaxHTTPError(response.status_code, response.text)
    return extract_next_data(response.text)


# TODO: Validate
def show(show_id: str, season_number: int | None = None) -> dict[str, Any]:
    season_segment = "" if season_number is None else f"s{season_number}/"
    return _get(f"https://www.hbomax.com/shows/{season_segment}{show_id}")


# TODO: Validate
def movie(movie_id: str) -> dict[str, Any]:
    return _get(f"https://www.hbomax.com/movies/{movie_id}")


# TODO: Validate
def content(page: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = page["props"]["pageProps"]["mappedData"]["idref14"]
    return mapped
