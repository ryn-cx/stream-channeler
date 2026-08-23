# TODO: Validate
from datetime import datetime
from functools import cache
from http import HTTPStatus
from typing import Any
from urllib.parse import quote, urlencode
from uuid import uuid4

import httpx

from plugins.utils.get_around_client import get_around_client


# TODO: Validate
class RokuHTTPError(Exception):
    # TODO: Validate
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.status_code = response.status_code
        super().__init__(
            f"Unexpected response status code: {response.status_code}\n{response.text}",
        )


# TODO: Validate
class RokuResourceNotFoundError(RokuHTTPError):
    pass


# TODO: Validate
class RokuContentNotFoundError(RokuResourceNotFoundError):
    # TODO: Validate
    def __init__(self, content_identifier: str, response: httpx.Response) -> None:
        self.content_identifier = content_identifier
        super().__init__(response)


# TODO: Validate
@cache
def _session_identifier() -> str:
    return str(uuid4())


# TODO: Validate
def _time_zone_offset() -> str:
    offset = datetime.now().astimezone().strftime("%z")
    return f"{offset[:-2]}:{offset[-2:]}"


# TODO: Validate
def _get(endpoint: str, headers: dict[str, str]) -> httpx.Response:
    return get_around_client().get(
        f"https://therokuchannel.roku.com/{endpoint}",
        headers={
            "accept": "*/*",
            "x-roku-reserved-session-id": _session_identifier(),
            "x-roku-reserved-time-zone-offset": _time_zone_offset(),
            "x-roku-reserved-culture-code": "en-US",
            "x-roku-reserved-channel-store-code": "us",
            "x-roku-reserved-experiment-state": "W10=",
            "x-roku-reserved-experiment-configs": "e30=",
            "x-roku-reserved-amoeba-ids": "",
            **headers,
        },
    )


# TODO: Validate
def content(content_identifier: str) -> dict[str, Any]:
    query = urlencode(
        {
            "expand": (
                "next,"
                "credits,"
                "next.series,"
                "viewOptions,"
                "categoryObjects,"
                "viewOptions.providerDetails,"
                "series,"
                "season,"
                "episodes,"
                "season.episodes,"
                "season.episodes.viewOptions.providerDetails,"
                "seasons.episodes.viewOptions.providerDetails,"
                "seasons,"
                "seasons[0],"
                "seasons[0].episodes"
            ),
            "include": (
                "type,"
                "title,"
                "imageMap.detailPoster,"
                "imageMap.detailBackground,"
                "bobs.detailScreen,"
                "categoryObjects,"
                "runTimeSeconds,"
                "castAndCrew,"
                "savable,"
                "stationDma,"
                "kidsDirected,"
                "releaseDate,"
                "releaseYear,"
                "description,"
                "descriptions,"
                "indicators,"
                "genres,"
                "credits.birthDate,"
                "credits.meta,"
                "credits.order,"
                "credits.name,"
                "credits.role,"
                "credits.personId,"
                "credits.imageMap.detailPoster,"
                "parentalRatings,"
                "reverseChronological,"
                "contentRatingClass,"
                "languageDialogBody,"
                "detailScreenOptions,"
                "viewOptions,"
                "episodeNumber,"
                "seasonNumber,"
                "sportInfo,"
                "eventState,"
                "next.series.title,"
                "series.title,"
                "season,"
                "season.episodes.title,"
                "season.episodes.description,"
                "season.episodes.descriptions.40,"
                "season.episodes.descriptions.60,"
                "season.episodes.episodeNumber,"
                "season.episodes.seasonNumber,"
                "season.episodes.images,"
                "season.episodes.imageMap.grid,"
                "season.episodes.indicators,"
                "season.episodes.releaseDate,"
                "season.episodes.viewOptions.isUnlocked,"
                "season.episodes.viewOptions.media.duration,"
                "season.episodes.viewOptions.providerId,"
                "season.episodes.viewOptions.providerProductId,"
                "season.episodes.viewOptions.providerDetails.providerProductIds,"
                "seasons.title,"
                "seasons.seasonNumber,"
                "seasons.description,"
                "seasons.descriptions,"
                "seasons.releaseYear,"
                "seasons.castAndCrew,"
                "seasons.credits.birthDate,"
                "seasons.credits.meta,"
                "seasons.credits.order,"
                "seasons.credits.name,"
                "seasons.credits.role,"
                "seasons.credits.personId,"
                "seasons.credits.images,"
                "seasons.imageMap.detailBackground,"
                "seasons.episodes.title,"
                "seasons.episodes.description,"
                "seasons.episodes.descriptions.40,"
                "seasons.episodes.descriptions.60,"
                "seasons.episodes.episodeNumber,"
                "seasons.episodes.seasonNumber,"
                "seasons.episodes.images,"
                "seasons.episodes.imageMap.grid,"
                "seasons.episodes.indicators,"
                "seasons.episodes.releaseDate,"
                "seasons.episodes.viewOptions,"
                "seasons.episodes.viewOptions.isUnlocked,"
                "seasons.episodes.viewOptions.media.duration,"
                "seasons.episodes.viewOptions.providerId,"
                "seasons.episodes.viewOptions.providerProductId,"
                "seasons.episodes.viewOptions.providerDetails.providerProductIds,"
                "episodes.episodeNumber,"
                "episodes.seasonNumber,"
                "episodes.viewOptions,"
                "viewOptions.disabled,"
                "viewOptions.providerId,"
                "viewOptions.providerProductId,"
                "viewOptions.discreteLiveEvent,"
                "viewOptions.license,"
                "viewOptions.media,"
                "viewOptions.channelId,"
                "viewOptions.adsContentId,"
                "viewOptions.adsProviderId,"
                "viewOptions.playId,"
                "viewOptions.isUnlocked,"
                "viewOptions.providerName,"
                "viewOptions.bobs.detailScreen,"
                "viewOptions.mvpdLivefeedId"
            ),
            "filter": (
                "categoryObjects:genreAppropriate%20eq%20true,"
                "seasons.episodes:(not%20empty(viewOptions)):all"
            ),
            "featureInclude": "bookmark,watchlist,linearSchedule",
        },
    )
    endpoint = "api/v2/homescreen/content/" + quote(
        f"https://content.sr.roku.com/content/v1/roku-trc/{content_identifier}?{query}",
        safe="",
    )
    response = _get(
        endpoint,
        {"referer": f"https://therokuchannel.roku.com/details/{content_identifier}"},
    )

    if response.status_code == HTTPStatus.NOT_FOUND:
        raise RokuContentNotFoundError(content_identifier, response)
    if response.status_code != HTTPStatus.OK:
        raise RokuHTTPError(response)

    body: dict[str, Any] = response.json()
    return body
