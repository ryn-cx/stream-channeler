# TODO: Validate
"""The file Watchmode's listing of a title is read out of."""

from __future__ import annotations

from functools import cache
from typing import override

from wampi import Wampi
from wampi.exceptions import TitleNotFoundError
from wampi.title_sources.models import TitleSourcesModel

from app.config import settings
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import EndpointFile
from plugins.utils.get_around_client import get_around_client

# The region a title's listing is asked for. Watchmode answers with every region
# the key is enabled for when it is not told one, and a listing of the rest is
# both larger and of no use to a `User` watching from here.
REGION = "US"


# TODO: Validate
@cache
def wampi() -> Wampi:
    """Return a cached Wampi client."""
    return Wampi(
        api_key=settings.WATCHMODE_API_KEY,
        get_around_client=get_around_client(),
    )


# TODO: Validate
class TitleSources(EndpointFile[TitleSourcesModel]):
    """Every source Watchmode says a title can be watched through.

    The title is named by the id Watchmode takes, which is TMDB's own id behind
    a prefix saying which half of the catalogue it belongs to, so a title TMDB
    has just read in is looked up without anything being searched for.
    """

    API_ENDPOINT = wampi().title_sources

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self.API_ENDPOINT.download(self.unique_identifier, regions=REGION)

    # Occurs when Watchmode does not carry the title TMDB named.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, TitleNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid title {self.unique_identifier}"


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """Reaching the Watchmode file for a title."""

    # TODO: Validate
    def title_sources_file(self, title_key: str) -> TitleSources:
        """Return the listing file for the Watchmode title id `title_key`."""
        return TitleSources(self.session, self.plugin, title_key)
