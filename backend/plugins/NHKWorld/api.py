# TODO: Validate
from http import HTTPStatus
from typing import Any

import httpx

from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class NHKWorldHTTPError(Exception):
    # TODO: Validate
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        super().__init__(f"Unexpected response status code: {response.status_code}")


# TODO: Validate
class NHKWorldNotFoundError(NHKWorldHTTPError):
    pass


# TODO: Validate
def _request(
    endpoint: str,
    params: dict[str, Any],
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"https://api.nhkworld.jp/{endpoint}"

    if json_body is not None:
        response = get_around_client().post(url=url, json=json_body, timeout=30)
    else:
        response = get_around_client().get(url=url, params=params, timeout=30)

    if response.status_code != HTTPStatus.OK:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise NHKWorldNotFoundError(response)
        raise NHKWorldHTTPError(response)

    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def video_programs(program_id: str) -> dict[str, Any]:
    return _request(f"showsapi/v1/en/video_programs/{program_id}", {})


# TODO: Validate
def video_episodes(
    program_id: str | None = None,
    *,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    if program_id is None:
        endpoint = "showsapi/v1/en/video_episodes"
    else:
        endpoint = f"showsapi/v1/en/video_programs/{program_id}/video_episodes"
    return _request(endpoint, {"limit": limit, "offset": offset})


# TODO: Validate
def video_episodes_all(program_id: str | None = None) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = video_episodes(program_id, offset=offset)
        pages.append(page)
        pagination = page["pagination"]
        offset += pagination["count"]
        if pagination["next"] is None or pagination["count"] == 0:
            return pages


# TODO: Validate
def shows_search(query: str, *, from_: int = 0, size: int = 40) -> dict[str, Any]:
    index = "nhkworld@en@ondemand@vod@programs"
    body: dict[str, Any] = {
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "type": "cross_fields",
                            "fields": ["title^16", "description^1"],
                            "operator": "and",
                        },
                    },
                    {
                        "multi_match": {
                            "query": query,
                            "type": "cross_fields",
                            "fields": ["body^1"],
                            "operator": "and",
                        },
                    },
                ],
            },
        },
        "from": from_,
        "size": size,
        "_source": ["title", "description", "slug", "url", "thumbnail"],
    }
    return _request(f"nwapi/showssearch/v1/{index}/list.json", {}, json_body=body)
