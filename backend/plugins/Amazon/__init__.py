# TODO: Validate
"""Amazon Prime Video plugin."""

from __future__ import annotations

from typing import ClassVar, override

from app.canonical_shows.models import CanonicalShow
from app.shows.models import Show
from plugins.Amazon.handlers import AmazonURLHandler, DetailURLHandler
from plugins.Amazon.helpers import HelperMixin
from plugins.Amazon.source import SourceMixin
from plugins.Amazon.upsert import UpsertMixin
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Amazon(
    SourceMixin,
    UpsertMixin,
    HelperMixin,
    URLHandlerPlugin[AmazonURLHandler],
    # TODO: Temporarily disabled.
    register=False,
):
    """Amazon Prime Video plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS: ClassVar[tuple[type[AmazonURLHandler], ...]] = (DetailURLHandler,)
    TMDB_PROVIDER_NAMES = ("Amazon Prime Video", "Amazon Video", "Prime Video")
    FAVICON_URL = "https://www.amazon.com/favicon.ico"

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: CanonicalShow | None = None,
    ) -> list[URLImportResult]:
        self._supplied_canonical_show = canonical_show
        handler = self.get_url_handler(url)
        handler.raise_if_invalid()
        return [
            result
            for show in self._import_shows(handler.show_key)
            for result in handler.import_results(show)
        ]

    # TODO: Validate
    def _import_shows(self, show_key: str) -> list[Show]:
        """Return the title's show for every source it belongs to.

        A title can be watched more than one way, so more than one show can share
        its key, which is why the base single-show import is not used.
        """
        if shows := self._preload_show(show_key).all():
            return list(shows)

        _cache = self._download_show_files_and_children(show_key)
        return self._upsert_shows(self.source, show_key)

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "amazon.com"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon Prime Video"
