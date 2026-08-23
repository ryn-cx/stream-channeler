# TODO: Validate
from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any
from urllib.parse import quote

from plugins.utils.get_around_client import get_around_client

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)


# TODO: Validate
class AmazonError(Exception):
    response: str | dict[str, Any] | None = None


# TODO: Validate
class AmazonHTTPError(AmazonError):
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
class BotCheckError(AmazonHTTPError):
    pass


# TODO: Validate
class ResourceNotFoundError(AmazonHTTPError):
    pass


# TODO: Validate
class TitleNotFoundError(ResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        title_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.title_id = title_id
        super().__init__(status_code, response)


# TODO: Validate
class RedirectedError(AmazonError):
    # TODO: Validate
    def __init__(self, location: str, response: dict[str, Any]) -> None:
        self.location = location
        self.response = response
        super().__init__(f"Request was redirected to {location}")


# TODO: Validate
def _headers() -> dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Language": "en-US",
        "Referer": "https://www.primevideo.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


# TODO: Validate
def _get(
    url: str,
    params: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    response = get_around_client().get(
        url,
        params=params,
        headers={**_headers(), **headers},
    )

    if response.status_code != HTTPStatus.OK:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise ResourceNotFoundError(response.status_code, response.text)
        if response.status_code == HTTPStatus.SERVICE_UNAVAILABLE:
            raise BotCheckError(response.status_code, response.text)
        raise AmazonHTTPError(response.status_code, response.text)

    parsed: dict[str, Any] = response.json()
    if "redirect" in parsed:
        raise RedirectedError(parsed["redirect"], parsed)
    return parsed


# TODO: Validate
def _download_page(path: str, params: dict[str, Any]) -> dict[str, Any]:
    return _get(
        url=f"https://www.primevideo.com/region/na/{path}",
        params={**params, "dvWebAppClientVersion": "1.0.127846.0"},
        headers={"x-requested-with": "WebAppSPA"},
    )


# TODO: Validate
def _download_api(operation: str, params: dict[str, Any]) -> dict[str, Any]:
    return _get(
        url=f"https://www.primevideo.com/region/na/api/{operation}",
        params=params,
        headers={"x-requested-with": "XMLHttpRequest"},
    )


# TODO: Validate
def detail(title_id: str) -> dict[str, Any]:
    try:
        return _download_page(path=f"detail/{title_id}", params={})
    except ResourceNotFoundError as error:
        raise TitleNotFoundError(
            title_id,
            error.status_code,
            error.response,
        ) from error


# TODO: Validate
def detail_widgets(
    title_id: str,
    widget_token: str,
    widget_type: str = "EpisodeList",
) -> dict[str, Any]:
    widgets = json.dumps(
        [{"widgetType": widget_type, "widgetToken": quote(widget_token, safe="")}],
        separators=(",", ":"),
    )
    return _download_api(
        operation="getDetailWidgets",
        params={"titleID": title_id, "widgets": widgets},
    )


# TODO: Validate
def search(query: str) -> dict[str, Any]:
    return _download_page(path="search", params={"phrase": query})
