# TODO: Validate
"""The file Watchmode's listing of a title is read out of."""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from typing import Any, override

from wampi import Wampi
from wampi.exceptions import TitleNotFoundError
from wampi.title_sources import TitleSources as TitleSourcesEndpoint
from wampi.title_sources.models import TitleSourcesModel

from app.config import settings
from plugins.utils.base_plugin_v2.base import BasePlugin
from plugins.utils.base_plugin_v2.files import BaseFile, EndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def wampi() -> Wampi:
    """Return a cached Wampi client."""
    return Wampi(
        api_key=settings.WATCHMODE_API_KEY,
        get_around_client=get_around_client(),
    )


# TODO: Validate
class _TitleSources(EndpointFile[TitleSourcesModel]):
    """Every source Watchmode says a title can be watched through.

    The title is named by the id Watchmode takes, which is TMDB's own id behind
    a prefix saying which half of the catalogue it belongs to, so a title TMDB
    has just read in is looked up without anything being searched for.
    """

    # TODO: Validate
    @override
    def _endpoint(self) -> TitleSourcesEndpoint:
        return wampi().title_sources

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        # The region a title's listing is asked for. Watchmode answers with
        # every region the key is enabled for when it is not told one, and a
        # listing of the rest is both larger and of no use to a `User` watching
        # from here.
        return self._endpoint().download(self.unique_identifier, regions="US")

    # Occurs when Watchmode does not carry the title TMDB named.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, TitleNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid title {self.unique_identifier}"


# TODO: Validate
class FileMixin(BasePlugin):
    """Reaching the Watchmode file for a title."""

    # TODO: Validate
    def title_sources_file(self, title_key: str) -> _TitleSources:
        """Return the listing file for the Watchmode title id `title_key`."""
        return _TitleSources(self.session, self.plugin, title_key)

    # Watchmode stores no media of its own, so these abstract methods are no-ops.
    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return []

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        return []
