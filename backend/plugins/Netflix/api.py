# TODO: Validate
from __future__ import annotations

import uuid
from http import HTTPStatus
from typing import Any

from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class NetflixError(Exception):
    pass


# TODO: Validate
class NetflixHTTPError(NetflixError):
    # TODO: Validate
    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"Unexpected response status code: {status_code}\n{body}")


# TODO: Validate
class NetflixInvalidFileError(NetflixError):
    # TODO: Validate
    def __init__(self, field: str, expected: object = None) -> None:
        self.field = field
        self.expected = expected
        if expected is None:
            super().__init__(f"Downloaded file has no {field}")
        else:
            super().__init__(f"Downloaded file is not for {field} {expected!r}")


# TODO: Validate
def _headers(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/json",
        "Origin": "https://www.netflix.com",
        "Referer": "https://www.netflix.com/",
        "x-netflix.context.ui-flavor": "akira",
        "x-netflix.context.app-version": "v232a5da5",
        "x-netflix.context.locales": "en-us",
        "x-netflix.context.operation-name": payload["operationName"],
        "x-netflix.request.attempt": "1",
        "x-netflix.request.client.context": '{"appstate":"foreground"}',
    }


# TODO: Validate
def _post(payload: dict[str, Any]) -> dict[str, Any]:
    response = get_around_client().post(
        url="https://web.prod.cloud.netflix.com/graphql",
        json=payload,
        headers=_headers(payload),
    )

    if response.status_code != HTTPStatus.OK:
        raise NetflixHTTPError(response.status_code, response.text)

    body: dict[str, Any] = response.json()
    return body


# TODO: Validate
def _image_params(artwork_type: str, **features: bool) -> dict[str, Any]:
    return {
        "artworkType": artwork_type,
        "dimension": {"width": 342, "height": 192},
        "features": {"fallbackStrategy": "STILL", **features},
    }


# TODO: Validate
def lodp_title_and_plans_page(video_id: str | int) -> dict[str, Any]:
    payload = {
        "operationName": "LodpTitleAndPlansPageQuery",
        "variables": {
            "videoId": int(video_id),
            "opaqueImageFormat": "JPG",
            "transparentImageFormat": "PNG",
            "thumbnailVideoId": -1,
            "hasValidThumbnailVideoId": False,
            "useBakedInPlayThumbnail": False,
            "useFromWatchSupplements": False,
        },
        "extensions": {
            "persistedQuery": {
                "id": "807ffc59-06c3-45b1-bd84-b9b4136381fc",
                "version": 102,
            },
        },
    }
    data = _post(payload)
    videos = data.get("data", {}).get("videos") or [{}]
    if videos[0].get("videoId") != int(video_id):
        raise NetflixInvalidFileError(field="video id", expected=int(video_id))
    return data


# TODO: Validate
def search_page_results(
    search_term: str,
    end_cursor: str | None = None,
) -> dict[str, Any]:
    payload = {
        "operationName": "SearchPageQueryResults",
        "variables": {
            "imageParamsForStandardBoxart": _image_params("SDP"),
            "imageParamsForCloudGameBoxart": _image_params(
                "GAME_CLOUD_BOXART_HORIZONTAL_INCOMPATIBLE",
                topContentTypeBadge=True,
            ),
            "imageParamsForMobileGameBoxart": _image_params(
                "GAME_ICON_BOXART_HORIZONTAL_CARD",
                topContentTypeBadge=True,
            ),
            "pageSize": 48,
            "options": {
                "pageCapabilities": {
                    "base": {
                        "canHandlePlayingCloudGames": False,
                        "capabilitiesBySection": {
                            "pinotGallery": {
                                "base": {
                                    "capabilitiesBySectionTreatment": {
                                        "pinotCreatorHome": {
                                            "base": {
                                                "capabilitiesByEntityTreatment": {
                                                    "pinotStandardBoxshot": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "VIDEO",
                                                            ],
                                                        },
                                                    },
                                                    "pinotStandardCloudAppIcon": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "GAME",
                                                            ],
                                                        },
                                                    },
                                                    "pinotStandardMobileAppIcon": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "GAME",
                                                            ],
                                                        },
                                                    },
                                                    "pinotStandardDestination": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "GENERIC_CONTAINER",
                                                            ],
                                                        },
                                                    },
                                                },
                                                "maxTotalEntities": 300,
                                            },
                                        },
                                        "pinotStandard": {
                                            "base": {
                                                "capabilitiesByEntityTreatment": {
                                                    "pinotStandardBoxshot": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "VIDEO",
                                                            ],
                                                        },
                                                    },
                                                    "pinotStandardCloudAppIcon": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "GAME",
                                                            ],
                                                        },
                                                    },
                                                    "pinotStandardMobileAppIcon": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "GAME",
                                                            ],
                                                        },
                                                    },
                                                    "pinotStandardDestination": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "GENERIC_CONTAINER",
                                                            ],
                                                        },
                                                    },
                                                },
                                                "maxTotalEntities": 300,
                                            },
                                        },
                                    },
                                },
                            },
                            "pinotList": {
                                "base": {
                                    "capabilitiesBySectionTreatment": {
                                        "pinotSuggestions": {
                                            "base": {
                                                "capabilitiesByEntityTreatment": {
                                                    "pinotSuggestion": {
                                                        "base": {
                                                            "canHandleEntityKinds": [
                                                                "AUTOCOMPLETE",
                                                                "VIDEO",
                                                                "CHARACTER",
                                                                "GENERIC_CONTAINER",
                                                                "GENRE",
                                                                "PERSON",
                                                            ],
                                                        },
                                                    },
                                                },
                                                "maxTotalEntities": 100,
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "maxTotalSections": 2,
                    },
                    "canHandleComplexSectionId": True,
                    "canSupportPreLaunchGames": True,
                },
                "session": {"id": str(uuid.uuid4())},
            },
            "searchTerm": search_term,
            "endCursor": end_cursor,
        },
        "extensions": {
            "persistedQuery": {
                "id": "8d902979-56f2-4886-8c16-f8910f6b52ee",
                "version": 102,
            },
        },
    }
    data = _post(payload)
    if data.get("data", {}).get("page", {}).get("sections") is None:
        raise NetflixInvalidFileError(field="search page")
    return data
