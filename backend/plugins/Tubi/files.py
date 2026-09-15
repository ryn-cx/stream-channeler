# TODO: Validate
"""The files a Tubi title is read out of."""

from __future__ import annotations

from functools import cache
from typing import override

from plugi import Plugi
from plugi.content import Content as ContentEndpoint
from plugi.content.models import ContentModel
from plugi.exceptions import ContentNotFoundError

from plugins.utils.base_plugin.files import SingleArgEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def plugi() -> Plugi:
    return Plugi(get_around_client=get_around_client())


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
