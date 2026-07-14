# TODO: Validate
from functools import cache

from get_around import GetAround

from app.config import settings


@cache
def get_around_client() -> GetAround:
    return GetAround(
        server=settings.GET_AROUND_SERVER,
        client_id=settings.CF_ACCESS_CLIENT_ID,
        client_secret=settings.CF_ACCESS_CLIENT_SECRET,
    )
