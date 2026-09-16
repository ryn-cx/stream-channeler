# TODO: Validate
from functools import cache

from get_around import GetAround

from app.config import settings


# TODO: Validate
@cache
def get_around_client(*, proxy: bool = False) -> GetAround:
    if proxy and not settings.PROXY:
        msg = "PROXY is not set, but a proxied client was asked for."
        raise ValueError(msg)
    return GetAround(
        server=settings.GET_AROUND_SERVER,
        client_id=settings.CF_ACCESS_CLIENT_ID,
        client_secret=settings.CF_ACCESS_CLIENT_SECRET,
        proxy=settings.PROXY if proxy else None,
    )
