# TODO: Validate
from functools import cache

from get_around import GetAround

from app.config import settings


# TODO: Validate
@cache
def proxy_client() -> GetAround:
    if settings.PROXY:
        return GetAround(proxy=settings.PROXY)
    return GetAround()
