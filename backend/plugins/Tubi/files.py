# TODO: Validate
"""The files a Tubi title is read out of."""

from __future__ import annotations

from datetime import datetime
from functools import cache
from typing import override

from plugi import Plugi
from plugi.content import Content as ContentEndpoint
from plugi.content.models import ContentModel
from plugi.exceptions import ContentNotFoundError
from plugi.sitemap import Sitemap as SitemapEndpoint
from plugi.sitemap import SitemapIndex as SitemapIndexEndpoint

from app.utils import tz_datetime
from plugins.utils.base_plugin.files import (
    NoArgsEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.constants import COMPLETE_CATALOG_UPDATE_INTERVAL
from plugins.utils.proxy_client import proxy_client


# TODO: Validate
@cache
def plugi() -> Plugi:
    return Plugi(get_around_client=proxy_client())


# TODO: Validate
class ContentFile(SingleArgEndpointFile[ContentModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ContentEndpoint:
        return plugi().content

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ContentNotFoundError)


# TODO: Validate
class SitemapIndexFile(NoArgsEndpointFile[list[str]]):
    unique_identifier = "sitemap_index"

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".xml"

    # TODO: Validate
    @override
    def _endpoint(self) -> SitemapIndexEndpoint:
        return plugi().sitemap_index


# TODO: Validate
class SitemapFile(SingleArgEndpointFile[list[str]]):
    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".xml"

    # TODO: Validate
    @override
    def _endpoint(self) -> SitemapEndpoint:
        return plugi().sitemap
