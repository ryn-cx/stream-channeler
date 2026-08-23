# TODO: Validate
"""The file Watchmode's listing of a title is read out of."""

from __future__ import annotations

from typing import Any, override

from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import EndpointJSON
from plugins.WatchMode import api

# The region a title's listing is asked for. Watchmode answers with every region
# the key is enabled for when it is not told one, and a listing of the rest is
# both larger and of no use to a `User` watching from here.
REGION = "US"


# TODO: Validate
class WatchModeJSON(EndpointJSON[list[dict[str, Any]]]):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return self.raise_if_not_is_instance(raw, list)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)


# TODO: Validate
class TitleSources(WatchModeJSON):
    """Every source Watchmode says a title can be watched through.

    The title is named by the id Watchmode takes, which is TMDB's own id behind
    a prefix saying which half of the catalogue it belongs to, so a title TMDB
    has just read in is looked up without anything being searched for.
    """

    # Occurs when Watchmode does not carry the title TMDB named.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.WatchModeResourceNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid title {self.unique_identifier}"

    # TODO: Validate
    @override
    def _fetch(self) -> list[dict[str, Any]]:
        return api.title_sources(
            self.unique_identifier,
            regions=REGION,
        )


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """Reaching the Watchmode file for a title."""

    # TODO: Validate
    def title_sources_file(self, title_key: str) -> TitleSources:
        """Return the listing file for the Watchmode title id `title_key`."""
        return TitleSources(self.session, self.plugin, title_key)
