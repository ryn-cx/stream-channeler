# TODO: Validate
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from functools import cache
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class PlutoError(Exception):
    response: str | dict[str, Any] | list[Any] | None = None


# TODO: Validate
class PlutoHTTPError(PlutoError):
    # TODO: Validate
    def __init__(
        self,
        status_code: int,
        response: str | dict[str, Any] | list[Any] | None,
    ) -> None:
        self.status_code = status_code
        self.response = response
        super().__init__(f"Unexpected response status code: {status_code}")


# TODO: Validate
class PlutoResourceNotFoundError(PlutoHTTPError):
    pass


# TODO: Validate
class PlutoSeriesNotFoundError(PlutoResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        series_id: str,
        status_code: int,
        response: str | dict[str, Any] | list[Any] | None,
    ) -> None:
        self.series_id = series_id
        super().__init__(status_code, response)


# TODO: Validate
class PlutoItemNotFoundError(PlutoResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        item_ids: list[str],
        status_code: int,
        response: str | dict[str, Any] | list[Any] | None,
    ) -> None:
        self.item_ids = item_ids
        super().__init__(status_code, response)


# TODO: Validate
class PlutoPageOutOfRangeError(PlutoError, ValueError):
    # TODO: Validate
    def __init__(self, page: int, response: dict[str, Any]) -> None:
        self.page = page
        self.response = response
        super().__init__(f"Requested page {page} is out of range")


# TODO: Validate
class PlutoUnknownServerError(PlutoError, KeyError):
    # TODO: Validate
    def __init__(self, server: str, servers: dict[str, str]) -> None:
        self.server = server
        self.servers = servers
        super().__init__(f"Boot response has no host for server {server!r}")


# TODO: Validate
class _Session:
    # TODO: Validate
    def __init__(self) -> None:
        self.client_id = str(uuid4())
        self.token = ""
        self.servers: dict[str, str] = {}
        self.expires_at = datetime.now(tz=UTC)

    # TODO: Validate
    def _refresh_if_needed(self) -> None:
        if not self.token or self.expires_at < datetime.now(tz=UTC):
            self._download()

    # TODO: Validate
    def _download(self) -> None:
        response = get_around_client().get(
            "https://boot.pluto.tv/v4/start",
            params={
                "appName": "web",
                "appVersion": "9.22.0",
                "deviceVersion": "153.0.0",
                "deviceModel": "web",
                "deviceMake": "firefox",
                "deviceType": "web",
                "clientID": self.client_id,
                "clientModelNumber": "1.0.0",
                "serverSideAds": "false",
                "drmCapabilities": "widevine:L3",
                "blockingMode": "",
                "notificationVersion": "1",
                "appLaunchCount": "0",
                "clientTime": datetime.now(tz=UTC).isoformat(timespec="milliseconds"),
            },
            headers={"origin": "https://pluto.tv", "referer": "https://pluto.tv/"},
        )
        if response.status_code != HTTPStatus.OK:
            raise PlutoHTTPError(response.status_code, response.text)

        parsed = response.json()
        self.token = parsed["sessionToken"]
        self.servers = parsed.get("servers") or {}
        self.expires_at = datetime.now(tz=UTC) + timedelta(
            seconds=parsed["refreshInSec"],
        )

    # TODO: Validate
    def authorization(self) -> str:
        self._refresh_if_needed()
        return f"Bearer {self.token}"

    # TODO: Validate
    def server_url(self, server: str) -> str:
        self._refresh_if_needed()
        url = self.servers.get(server) or {
            "vod": "https://service-vod.clusters.pluto.tv",
            "search": "https://service-media-search.clusters.pluto.tv",
        }.get(server)
        if not url:
            raise PlutoUnknownServerError(server, self.servers)
        return url


# TODO: Validate
@cache
def _session() -> _Session:
    return _Session()


# TODO: Validate
def _get(
    server: str,
    endpoint: str,
    params: dict[str, Any],
) -> Any:  # noqa: ANN401 - Some endpoints return a JSON array.
    session = _session()
    response = get_around_client().get(
        f"{session.server_url(server)}/{endpoint}",
        params=params,
        headers={
            "origin": "https://pluto.tv",
            "referer": "https://pluto.tv/",
            "authorization": session.authorization(),
        },
    )

    if response.status_code != HTTPStatus.OK:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise PlutoResourceNotFoundError(response.status_code, response.text)
        raise PlutoHTTPError(response.status_code, response.text)

    return response.json()


# TODO: Validate
def items(item_ids: Sequence[str]) -> list[dict[str, Any]]:
    response: list[dict[str, Any]] = _get(
        "vod",
        "v4/vod/items",
        {"ids": ",".join(item_ids)},
    )
    if not response:
        raise PlutoItemNotFoundError(list(item_ids), HTTPStatus.OK, response)
    return response


# TODO: Validate
def seasons(series_id: str, *, offset: int = 1000, page: int = 1) -> dict[str, Any]:
    try:
        response: dict[str, Any] = _get(
            "vod",
            f"v4/vod/series/{series_id}/seasons",
            {"offset": offset, "page": page},
        )
    except PlutoResourceNotFoundError as error:
        raise PlutoSeriesNotFoundError(
            series_id,
            error.status_code,
            error.response,
        ) from error

    if not response.get("seasons"):
        if page > 1:
            raise PlutoPageOutOfRangeError(page, response)
        raise PlutoSeriesNotFoundError(series_id, HTTPStatus.OK, response)
    return response
