# TODO: Validate
from __future__ import annotations

import datetime
from functools import cache
from http import HTTPStatus
from json import JSONDecodeError, loads
from time import sleep
from typing import Any

import httpx
from get_around import GetAround

from app.config import settings
from plugins.JustWatch import queries
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class JustWatchError(Exception):
    response: Any = None


# TODO: Validate
class JustWatchHTTPError(JustWatchError):
    # TODO: Validate
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        try:
            self.response = loads(body)
        except JSONDecodeError:
            self.response = body
        super().__init__(f"Unexpected response status code: {status_code}\n{body}")


# TODO: Validate
class JustWatchGraphQLError(JustWatchError):
    # TODO: Validate
    def __init__(self, errors: list[dict[str, Any]], response: Any) -> None:  # noqa: ANN401
        self.errors = errors
        self.response = response
        super().__init__(f"GraphQL errors occurred: {errors}")


# TODO: Validate
class JustWatchInvalidFileError(JustWatchError):
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


# TODO: Validate
@cache
def _client() -> GetAround:
    # Get Around sometimes gets blocked without a 5 second delay.
    if settings.PROXY:
        return GetAround(proxy=settings.PROXY)
    return get_around_client()


# TODO: Validate
def _sleep_time() -> float:
    return 0 if settings.PROXY else 5


# TODO: Validate
def _post(
    operation_name: str,
    query: str,
    variables: dict[str, Any],
) -> dict[str, Any]:
    response = _client().post(
        "https://apis.justwatch.com/graphql",
        json={
            "operationName": operation_name,
            "query": query,
            "variables": variables,
        },
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 11.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.6998.166 Safari/537.36",
            "Referer": "https://www.justwatch.com/",
            "Origin": "https://www.justwatch.com",
        },
        timeout=30,
    )

    if response.status_code != HTTPStatus.OK:
        raise JustWatchHTTPError(response.status_code, response.text)

    output: dict[str, Any] = response.json()

    if output.get("errors"):
        raise JustWatchGraphQLError(output["errors"], output)

    sleep(_sleep_time())

    return output


# TODO: Validate
def providers_locale(locale: str) -> list[dict[str, Any]]:
    response = httpx.get(
        f"https://apis.justwatch.com/content/providers/locale/{locale}",
    )
    response.raise_for_status()
    providers: list[dict[str, Any]] = response.json()
    return providers


# TODO: Validate
def buy_box_offers(node_id: str) -> dict[str, Any]:
    data = _post(
        "GetBuyBoxOffers",
        queries.BUY_BOX_OFFERS,
        {
            "platform": "WEB",
            "fallbackToForeignOffers": False,
            "excludePackages": [
                "3ca",
                "als",
                "amo",
                "cgv",
                "chi",
                "cnv",
                "cut",
                "daf",
                "kod",
                "koc",
                "mrp",
                "mte",
                "mvt",
                "nxp",
                "org",
                "ply",
                "rvl",
                "tak",
                "tbv",
                "tf1",
                "uat",
                "vld",
                "wa4",
                "wdt",
                "yot",
                "yrk",
            ],
            "nodeId": node_id,
            "country": "US",
            "language": "en",
        },
    )
    node = data.get("data", {}).get("node", {})
    if node.get("id") != node_id:
        raise JustWatchInvalidFileError(
            field="node id",
            expected=node_id,
            response=data,
        )
    return data


# TODO: Validate
def url_title_details(full_path: str) -> dict[str, Any]:
    data = _post(
        "GetUrlTitleDetails",
        queries.URL_TITLE_DETAILS,
        {
            "platform": "WEB",
            "excludeTextRecommendationTitle": True,
            "first": 10,
            "fallbackToForeignOffers": False,
            "excludePackages": [
                "3ca",
                "als",
                "amo",
                "cgv",
                "chi",
                "cnv",
                "cut",
                "daf",
                "kod",
                "koc",
                "mrp",
                "mte",
                "mvt",
                "nxp",
                "org",
                "ply",
                "rvl",
                "tak",
                "tbv",
                "tf1",
                "uat",
                "vld",
                "wa4",
                "wdt",
                "yot",
                "yrk",
            ],
            "fullPath": full_path,
            "language": "en",
            "country": "US",
            "episodeMaxLimit": 20,
        },
    )
    node = data.get("data", {}).get("urlV2", {}).get("node", {})
    if node.get("content", {}).get("fullPath") != full_path:
        raise JustWatchInvalidFileError(
            field="full path",
            expected=full_path,
            response=data,
        )
    return data


# TODO: Validate
def _season_episodes_page(node_id: str, offset: int) -> dict[str, Any]:
    data = _post(
        "GetSeasonEpisodes",
        queries.SEASON_EPISODES,
        {
            "nodeId": node_id,
            "country": "US",
            "language": "en",
            "platform": "WEB",
            "limit": 20,
            "offset": offset,
        },
    )
    node = data.get("data", {}).get("node", {})
    if node.get("id") != node_id:
        raise JustWatchInvalidFileError(
            field="node id",
            expected=node_id,
            response=data,
        )
    return data


# TODO: Validate
def season_episodes(node_id: str) -> list[dict[str, Any]]:
    offset = 0
    pages: list[dict[str, Any]] = []

    while True:
        page = _season_episodes_page(node_id, offset)
        pages.append(page)
        if len(page["data"]["node"]["episodes"]) < 20:  # noqa: PLR2004
            return pages
        offset += 20


# TODO: Validate
def _new_titles_page(
    source_key: str,
    new_titles_date: datetime.date,
    after: str | None,
) -> dict[str, Any]:
    data = _post(
        "GetNewTitles",
        queries.NEW_TITLES,
        {
            "after": after,
            "first": 10,
            "pageType": "NEW",
            "date": new_titles_date.isoformat(),
            "filter": {
                "ageCertifications": [],
                "excludeGenres": [],
                "excludeProductionCountries": [],
                "objectTypes": [],
                "productionCountries": [],
                "subgenres": [],
                "genres": [],
                "packages": [source_key],
                "excludeIrrelevantTitles": False,
                "presentationTypes": [],
                "monetizationTypes": [],
            },
            "language": "en",
            "country": "US",
            "priceDrops": False,
            "platform": "WEB",
            "showDateBadge": False,
            "availableToPackages": [source_key],
        },
    )
    if data.get("data", {}).get("newTitles", {}).get("edges") is None:
        raise JustWatchInvalidFileError(field="new titles", response=data)
    return data


# TODO: Validate
def new_titles(
    source_key: str,
    new_titles_date: datetime.date,
) -> list[dict[str, Any]]:
    after: str | None = None
    pages: list[dict[str, Any]] = []

    while True:
        page = _new_titles_page(source_key, new_titles_date, after)
        pages.append(page)

        page_info = page["data"]["newTitles"]["pageInfo"]
        if not page_info["hasNextPage"]:
            return pages

        after = page_info["endCursor"]


# TODO: Validate
def _new_title_buckets_page(new_after_cursor: str) -> dict[str, Any]:
    data = _post(
        "GetNewTitleBuckets",
        queries.NEW_TITLE_BUCKETS,
        {
            "first": 8,
            "bucketSize": 0,
            "groupBy": "DATE_PACKAGE",
            "pageType": "NEW",
            "country": "US",
            "newAfterCursor": new_after_cursor,
            "newTitlesFilter": {
                "ageCertifications": [],
                "excludeGenres": [],
                "excludeProductionCountries": [],
                "objectTypes": [],
                "productionCountries": [],
                "subgenres": [],
                "genres": [],
                "packages": [],
                "excludeIrrelevantTitles": False,
                "presentationTypes": [],
                "monetizationTypes": [],
            },
            "priceDrops": False,
        },
    )
    if data.get("data", {}).get("newTitleBuckets", {}).get("edges") is None:
        raise JustWatchInvalidFileError(field="new title buckets", response=data)
    return data


# TODO: Validate
def new_title_buckets(end_date: datetime.date) -> list[dict[str, Any]]:
    new_after_cursor = ""
    pages: list[dict[str, Any]] = []

    while True:
        page = _new_title_buckets_page(new_after_cursor)
        pages.append(page)

        buckets = page["data"]["newTitleBuckets"]
        last_edge = buckets["edges"][-1]
        if datetime.date.fromisoformat(last_edge["key"]["date"]) < end_date:
            return pages

        if not buckets["pageInfo"]["hasNextPage"]:
            return pages

        new_after_cursor = buckets["pageInfo"]["endCursor"]
