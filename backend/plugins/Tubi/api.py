# TODO: Validate
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import cache
from http import HTTPStatus
from typing import Any

from plugins.utils.get_around_client import get_around_client

WEBSITE = "https://tubitv.com"
PLATFORM = "web"
ACCOUNT_DOMAIN = "account.production-public.tubi.io"
ALGORITHM = "TUBI-HMAC-SHA256"
SIGNED_HEADERS = "content-type"
PAGE_SIZE_IN_SEASON = 20


# TODO: Validate
class TubiHTTPError(Exception):
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
class TubiAuthorizationError(TubiHTTPError):
    pass


# TODO: Validate
class TubiResourceNotFoundError(TubiHTTPError):
    pass


# TODO: Validate
class TubiContentNotFoundError(TubiResourceNotFoundError):
    # TODO: Validate
    def __init__(
        self,
        content_id: str,
        status_code: int,
        response: str | dict[str, Any] | None,
    ) -> None:
        self.content_id = content_id
        super().__init__(status_code, response)


# TODO: Validate
@cache
def _device_id() -> str:
    return str(uuid.uuid4())


_access_token_value = ""
_token_expires_at = datetime.now(tz=UTC)


# TODO: Validate
def _headers() -> dict[str, str]:
    return {
        "Accept": "*/*",
        "Accept-Language": "en-US",
        "Origin": WEBSITE,
        "Referer": f"{WEBSITE}/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
    }


# TODO: Validate
def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode()


# TODO: Validate
def _signature_params(
    body: str,
    signing_key: str,
    signed_at: str,
) -> dict[str, str | int]:
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    canonical_request = (
        f"POST\n/device/anonymous/token\n\n{SIGNED_HEADERS}:application/json\n"
        f"\n{SIGNED_HEADERS}\n{body_hash}"
    )
    canonical_hash = hashlib.sha256(canonical_request.encode()).hexdigest()
    string_to_sign = f"{ALGORITHM}\n{signed_at}\n{canonical_hash}"

    key = b"TUBI" + base64.b64decode(signing_key)
    date = signed_at.split("T", maxsplit=1)[0]
    key = hmac.new(key, date.encode(), hashlib.sha256).digest()
    key = hmac.new(key, b"tubi_request", hashlib.sha256).digest()
    signature = hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    return {
        "X-Tubi-Algorithm": ALGORITHM,
        "X-Tubi-Date": signed_at,
        "X-Tubi-Expires": 30,
        "X-Tubi-SignedHeaders": SIGNED_HEADERS,
        "X-Tubi-Signature": signature,
    }


# TODO: Validate
def _download_signing_key(verifier: str) -> dict[str, str]:
    response = get_around_client().post(
        f"https://{ACCOUNT_DOMAIN}/device/anonymous/signing_key",
        json={
            "challenge": _code_challenge(verifier),
            "version": "1.0.0",
            "platform": PLATFORM,
            "device_id": _device_id(),
        },
        headers={**_headers(), "content-type": "application/json"},
    )
    if response.status_code != HTTPStatus.OK:
        raise TubiAuthorizationError(response.status_code, response.text)
    signing_key: dict[str, str] = response.json()
    return signing_key


# TODO: Validate
def _download_access_token() -> None:
    global _access_token_value, _token_expires_at  # noqa: PLW0603

    verifier = secrets.token_hex(16)
    signing_key = _download_signing_key(verifier)
    body = json.dumps(
        {
            "verifier": verifier,
            "id": signing_key["id"],
            "platform": PLATFORM,
            "device_id": _device_id(),
        },
        separators=(",", ":"),
    )
    signed_at = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    response = get_around_client().post(
        f"https://{ACCOUNT_DOMAIN}/device/anonymous/token",
        content=body,
        params=_signature_params(body, signing_key["key"], signed_at),
        headers={**_headers(), "content-type": "application/json"},
    )
    if response.status_code != HTTPStatus.OK:
        raise TubiAuthorizationError(response.status_code, response.text)

    parsed = response.json()
    _access_token_value = parsed["access_token"]
    _token_expires_at = datetime.now(tz=UTC) + timedelta(seconds=parsed["expires_in"])


# TODO: Validate
def _access_token() -> str:
    if not _access_token_value or _token_expires_at < datetime.now(tz=UTC):
        _download_access_token()
    return _access_token_value


# TODO: Validate
def _get(
    endpoint: str,
    params: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    response = get_around_client().get(
        f"https://content-cdn.production-public.tubi.io/{endpoint}",
        params={
            "app_id": "tubitv",
            "platform": PLATFORM,
            "device_id": _device_id(),
            **params,
        },
        headers={
            **_headers(),
            "Accept-Version": "~5.0.0",
            **headers,
            "Authorization": f"Bearer {_access_token()}",
        },
    )

    if response.status_code != HTTPStatus.OK:
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise TubiResourceNotFoundError(response.status_code, response.text)
        raise TubiHTTPError(response.status_code, response.text)

    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def content(
    content_id: str,
    *,
    season: int | None = None,
    page_in_season: int = 1,
    page_size_in_season: int = PAGE_SIZE_IN_SEASON,
    include_channels: bool = True,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "content_id": content_id,
        "include_channels": str(include_channels).lower(),
        "limit_resolutions[]": ["h264_1080p", "h265_1080p"],
        "video_resources[]": [
            "hlsv6_widevine_nonclearlead",
            "hlsv6_playready_psshv0",
            "hlsv6_fairplay",
            "hlsv6",
        ],
        "creator_tensor_app_images[logo]": "w100h100_logo",
        "creator_tensor_app_images[title_art]": "w430h180_title",
        "images[posterarts]": "w408h583_poster",
        "images[hero_422]": "w422h360_hero",
        "images[hero_feature_desktop_tablet]": "w1920h768_hero",
        "images[hero_feature_large_mobile]": "w960h480_hero",
        "images[hero_feature_small_mobile]": "w540h450_hero",
        "images[hero_feature]": "w375h355_hero",
        "images[hero_16x9]": "w1280h720_hero",
        "images[landscape_images]": "w978h549_landscape",
        "images[linear_larger_poster]": "w978h549_landscape",
        "images[backgrounds]": "w1614h906_background",
        "images[title_art]": "w430h180_title",
    }
    if season is not None:
        params["pagination[season]"] = season
        params["pagination[page_in_season]"] = page_in_season
        params["pagination[page_size_in_season]"] = page_size_in_season

    try:
        return _get(
            "api/v3/content",
            params,
            {"x-capability": '{"content_types":["se"]}'},
        )
    except TubiResourceNotFoundError as error:
        raise TubiContentNotFoundError(
            content_id,
            error.status_code,
            error.response,
        ) from error
