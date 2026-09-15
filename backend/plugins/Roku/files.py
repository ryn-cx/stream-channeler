# TODO: Validate
"""The files The Roku Channel is read out of.

One endpoint covers every kind of content, so a movie, a series, a season and an
episode are all read out of the same file under an id of their own.
"""

from __future__ import annotations

from abc import ABC
from functools import cache
from typing import override

from nana import Nana
from nana.content import Content as ContentEndpoint
from nana.content.models import ContentModel
from nana.exceptions import ContentNotFoundError

from plugins.utils.base_plugin.files import SingleArgEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def nana() -> Nana:
    return Nana(get_around_client=get_around_client())


# TODO: Validate
class BaseContentFile(SingleArgEndpointFile[ContentModel], ABC):
    """What every file read off the content endpoint has in common."""

    # TODO: Validate
    @override
    def _endpoint(self) -> ContentEndpoint:
        return nana().content


# TODO: Validate
class ContentFile(BaseContentFile):
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ContentNotFoundError)


# TODO: Validate
class SeasonEpisodesFile(BaseContentFile):
    pass
