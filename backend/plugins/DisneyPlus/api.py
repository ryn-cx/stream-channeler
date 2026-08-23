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
class DisneyPlusHTTPError(Exception):
    # TODO: Validate
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Unexpected response status code: {status_code}")


# TODO: Validate
class DisneyPlusExtractionError(Exception):
    pass


# TODO: Validate
def _get(url: str) -> dict[str, Any]:
    response = get_around_client().get(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.disneyplus.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0, i",
        },
        follow_redirects=True,
    )
    if response.status_code != HTTPStatus.OK:
        raise DisneyPlusHTTPError(response.status_code, response.text)

    match = _NEXT_DATA_REGEX.search(response.text)
    if match is None:
        msg = "Could not find __NEXT_DATA__ script tag in the page HTML"
        raise DisneyPlusExtractionError(msg)

    parsed: dict[str, Any] = json.loads(match.group("json"))
    return parsed


# TODO: Validate
def entity(entity_id: str, season_id: str | None = None) -> dict[str, Any]:
    url = f"https://www.disneyplus.com/browse/entity-{entity_id}"
    if season_id is not None:
        url = f"{url}?season={season_id}"
    return _get(url)


# TODO: Validate
def group_main_content(page: dict[str, Any]) -> dict[str, Any]:
    main_content = page["props"]["pageProps"]["stitchDocument"]["mainContent"]
    grouped: dict[str, Any] = {}
    for item in main_content:
        key = item["_type"]
        if key == "ExperimentContainer":
            continue
        if key == "CustomHTML":
            grouped.setdefault(key, []).append(item)
        elif key == "Section":
            grouped.setdefault(key, item)
        else:
            if key in grouped:
                msg = f"Duplicate single-item _type {key!r} in main content."
                raise ValueError(msg)
            grouped[key] = item
    return grouped
