# TODO: Validate
from functools import cache

import httpx
from get_around import GetAround

from app.config import settings


# TODO: Validate
@cache
def proxy_client() -> GetAround:
    return httpx.Client(proxy=settings.PROXY or None, timeout=30)  # type: ignore[return-value]
