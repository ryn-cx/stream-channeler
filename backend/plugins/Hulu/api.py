# TODO: Validate
import random
from collections.abc import Mapping
from functools import cache
from typing import Any

from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class HuluError(Exception):
    pass


# TODO: Validate
class HuluHTTPError(HuluError):
    pass


# TODO: Validate
class HuluCookieError(HuluError):
    pass


# TODO: Validate
class HuluInvalidSeasonError(HuluError):
    # TODO: Validate
    def __init__(self, response: Mapping[str, Any]) -> None:
        self.response = response
        super().__init__("Invalid season number")


# TODO: Validate
@cache
def _fetch_cookie() -> str:
    response = get_around_client().get("https://www.hulu.com/")
    cookies: dict[str, str] = {}
    for set_cookie in response.headers.get_list("set-cookie"):
        name, separator, remainder = set_cookie.partition("=")
        if separator:
            cookies[name.strip()] = remainder.split(";", 1)[0].strip()
    if not cookies:
        msg = "No session cookie returned by https://www.hulu.com/"
        raise HuluCookieError(msg)
    return "; ".join(f"{name}={value}" for name, value in cookies.items())


# TODO: Validate
def _headers(referer: str) -> dict[str, str]:
    return {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
        "Origin": "https://www.hulu.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Cookie": _fetch_cookie(),
        "Priority": "u=4",
    }


# TODO: Validate
def _get(
    url: str,
    referer: str,
    params: dict[str, str] | tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    response = get_around_client().get(
        url,
        params=params,
        headers=_headers(referer),
    )
    if response.is_error:
        msg = f"Unexpected response status code: {response.status_code}"
        raise HuluHTTPError(msg)
    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def _hub(content_type: str, content_id: str) -> dict[str, Any]:
    return _get(
        f"https://discover.hulu.com/content/v5/hubs/{content_type}/{content_id}",
        f"https://www.hulu.com/{content_type}/{content_id}",
        {
            "schema": "3",
            "limit": "1999",
            "device_info": "web:4.44.1",
            "referralHost": "production",
            "cacheKey": str(random.random()),  # noqa: S311
            "pageType": "DETAILS",
        },
    )


# TODO: Validate
def series_hub(series_id: str) -> dict[str, Any]:
    return _hub("series", series_id)


# TODO: Validate
def movie_hub(movie_id: str) -> dict[str, Any]:
    return _hub("movie", movie_id)


# TODO: Validate
def episode_hub(episode_id: str) -> dict[str, Any]:
    return _get(
        f"https://discover.hulu.com/content/v5/hubs/episode/{episode_id}",
        f"https://www.hulu.com/watch/{episode_id}",
        {
            "schema": "3",
            "limit": "1999",
            "device_info": "web:4.44.1",
            "referralHost": "production",
            "pageType": "DETAILS",
        },
    )


# TODO: Validate
def season(series_id: str, season_number: int) -> dict[str, Any]:
    response = _get(
        f"https://discover.hulu.com/content/v5/hubs/series/{series_id}"
        f"/season/{season_number}",
        f"https://www.hulu.com/series/{series_id}",
        {
            "schema": "3",
            "limit": "1999",
            "offset": "0",
            "device_info": "web:4.44.1",
            "referralHost": "production",
        },
    )
    if not response["pagination"]["total_count"]:
        raise HuluInvalidSeasonError(response)
    return response


# TODO: Validate
def search_entity(query: str) -> dict[str, Any]:
    return _get(
        "https://discover.hulu.com/content/v5/search/entity",
        "https://www.hulu.com/search",
        (
            ("language", "en"),
            ("device_context_id", "2"),
            ("search_query", query),
            ("limit", "64"),
            ("include_offsite", "true"),
            ("schema", "3"),
            ("device_info", "web:4.44.1"),
            ("referralHost", "production"),
            ("keywords", query),
            ("type", "entity"),
            ("limit", "64"),
        ),
    )
