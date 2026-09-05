# TODO: Validate
"""The files a Tubi title is read out of."""

from __future__ import annotations

from functools import cache
from typing import override

from plugi import Plugi
from plugi.content import Content as ContentEndpoint
from plugi.content.models import ContentModel
from plugi.exceptions import ContentNotFoundError

from plugins.utils.base_plugin_v3.files import EndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def plugi() -> Plugi:
    return Plugi(get_around_client=get_around_client())


# TODO: Validate
class ContentFile(EndpointFile[ContentModel]):
    @override
    def _endpoint(self) -> ContentEndpoint:
        return plugi().content

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ContentNotFoundError)

    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid content_id {self.unique_identifier}"
