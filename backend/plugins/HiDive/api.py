# TODO: Validate
from __future__ import annotations

from datetime import datetime
from typing import Any

from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class HiDiveError(Exception):
    pass


# TODO: Validate
class HiDiveHTTPError(HiDiveError):
    # TODO: Validate
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"Unexpected response status code: {status_code}")


_authentication_values: dict[str, str] = {}


# TODO: Validate
def _authentication() -> dict[str, str]:
    if not _authentication_values:
        response = get_around_client().get(
            "https://dce-frontoffice.imggaming.com/api/v1/init/"
            "?lk=language"
            "&pk=subTitleLanguage"
            "&pk=audioLanguage"
            "&pk=autoAdvance"
            "&pk=pluginAccessTokens"
            "&pk=videoBackgroundAutoPlay"
            "&readLicences=true"
            "&countEvents=LIVE"
            "&menuTargetPlatform=WEB"
            "&readIconStore=ENABLED",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Linux; Android 10; K) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/134.0.0.0 Mobile Safari/537.3"
                ),
                "Origin": "https://www.hidive.com",
                "Referer": "https://www.hidive.com/",
                "x-api-key": "857a1e5d-e35e-4fdf-805b-a87b6f8364bf",
            },
        )
        body = response.json()
        _authentication_values["realm"] = body["settings"]["realm"]
        _authentication_values["authorisation_token"] = body["authentication"][
            "authorisationToken"
        ]
    return _authentication_values


# TODO: Validate
def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    authentication = _authentication()
    response = get_around_client().get(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 10; K) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/134.0.0.0 Mobile Safari/537.3"
            ),
            "authorization": f"Bearer {authentication['authorisation_token']}",
            "x-api-key": "857a1e5d-e35e-4fdf-805b-a87b6f8364bf",
            "Origin": "https://www.hidive.com",
            "Referer": "https://www.hidive.com/",
            "Realm": authentication["realm"],
        },
        params=params,
    )

    if not response.is_success:
        raise HiDiveHTTPError(response.status_code)

    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def vod(vod_id: int | str) -> dict[str, Any]:
    return _get(
        "https://dce-frontoffice.imggaming.com/api/v1/view",
        {
            "type": "vod",
            "id": int(vod_id),
            "timezone": "America/Los_Angeles",
        },
    )


# TODO: Validate
def season(season_id: int | str) -> dict[str, Any]:
    return _get(
        "https://dce-frontoffice.imggaming.com/api/v1/view",
        {
            "type": "season",
            "id": int(season_id),
            "timezone": "America/Los_Angeles",
        },
    )


# TODO: Validate
def series(series_id: int | str) -> dict[str, Any]:
    return _get(
        "https://dce-frontoffice.imggaming.com/api/v1/view",
        {
            "type": "series",
            "id": int(series_id),
            "timezone": "America/Los_Angeles",
        },
    )


# TODO: Validate
def search(query: str) -> dict[str, Any]:
    return _get(
        "https://search.dce-prod.dicelaboratory.com/search",
        {
            "query": query,
            "timezone": "America/Los_Angeles",
        },
    )


# TODO: Validate
def schedule(
    from_: datetime | None = None,
    last_seen: str | None = None,
) -> dict[str, Any]:
    params: dict[str, str | int] = {
        "timezone": "America/Los_Angeles",
        "groupsPerPage": 7,
        "itemsPerGroup": 7,
    }

    if from_:
        params["from"] = from_.strftime("%Y-%m-%dT%H:%M:%S")

    if last_seen:
        params["lastSeen"] = last_seen

    return _get(
        "https://dce-frontoffice.imggaming.com/api/v1/view/schedule",
        params,
    )


# TODO: Validate
def schedule_until_datetime(
    end_datetime: datetime,
    from_: datetime | None = None,
) -> list[dict[str, Any]]:
    all_schedules: list[dict[str, Any]] = []
    last_seen: str | None = None

    while True:
        downloaded = schedule(from_=from_, last_seen=last_seen)
        from_ = None
        all_schedules.append(downloaded)

        group_list = extract_group_list(downloaded)

        actions = group_list["attributes"].get("actions")
        if actions:
            last_seen = actions["next"]["data"]["lastSeen"]
        else:
            return all_schedules

        if all(
            datetime.fromisoformat(
                group["attributes"]["title"]["attributes"]["text"],
            ).astimezone()
            >= end_datetime
            for group in group_list["attributes"]["groups"]
        ):
            return all_schedules


# TODO: Validate
def _single_match(
    matches: list[dict[str, Any]],
    type_description: str,
) -> dict[str, Any]:
    if not matches:
        msg = f"No {type_description} element found"
        raise ValueError(msg)
    if len(matches) > 1:
        msg = f"Too many {type_description} elements found"
        raise ValueError(msg)
    return matches[0]


# TODO: Validate
def extract_element(data: dict[str, Any], field_type: str) -> dict[str, Any]:
    return _single_match(
        [element for element in data["elements"] if element["$type"] == field_type],
        field_type,
    )


# TODO: Validate
def extract_typed_element(
    data: dict[str, Any],
    field_type: str,
    attribute_type: str,
) -> dict[str, Any]:
    return _single_match(
        [
            element
            for element in data["elements"]
            if element["$type"] == field_type
            and element["attributes"].get("type") == attribute_type
        ],
        f"{attribute_type!r} {field_type}",
    )


# TODO: Validate
def extract_hero(data: dict[str, Any]) -> dict[str, Any]:
    return extract_element(data, "hero")


# TODO: Validate
def extract_bucket_season(data: dict[str, Any]) -> dict[str, Any]:
    return extract_typed_element(data, "bucket", "season")


# TODO: Validate
def extract_group_list(data: dict[str, Any]) -> dict[str, Any]:
    return extract_element(data, "groupList")
