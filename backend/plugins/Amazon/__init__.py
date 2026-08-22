# TODO: Validate
"""Amazon Prime Video plugin."""

from __future__ import annotations

from typing import override

from app.canonical_media.service import add_canonical_show
from app.shows.models import Show
from plugins.Amazon.media_info import MediaInfoMixin
from plugins.Amazon.search import SearchMixin
from plugins.Amazon.source import SourceMixin
from plugins.Amazon.upsert import UpsertMixin
from plugins.Amazon.url_handlers import (
    AmazonDetailURLHandler,
    AmazonURLHandler,
    PrimeVideoDetailURLHandler,
    WatchAmazonDetailURLHandler,
)
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class Amazon(
    UpsertMixin,
    SearchMixin,
    MediaInfoMixin,
    SourceMixin,
    URLHandlerPlugin[AmazonURLHandler],
    register=False,
):
    """Amazon Prime Video plugin."""

    _VERSION = "0.0.1"
    _URL_HANDLERS = (
        # Must be listed first: a share link's path is also a detail path, and
        # only this one carries the id in the query rather than the path.
        WatchAmazonDetailURLHandler,
        PrimeVideoDetailURLHandler,
        AmazonDetailURLHandler,
    )
    TMDB_PROVIDER_NAMES = ("Amazon Prime Video", "Amazon Video", "Prime Video")
    FAVICON_URL = "https://www.primevideo.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        # Prime Video is read out of its own website, and Amazon's is listed as
        # well because a link to a title on it is a link to the same title.
        # watch.amazon.com is the domain Amazon writes a share link under, and
        # is its own entry because only an optional `www.` is read off a domain.
        return ["primevideo.com", "amazon.com", "watch.amazon.com"]

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon Prime Video"

    # TODO: Validate
    @override  # Writes the title into every source it can be watched through.
    def _import_handler(
        self,
        handler: AmazonURLHandler,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = handler.show_key
        if not force and (shows := self._preload_show(show_key).all()):
            if canonical_show:
                for show in shows:
                    add_canonical_show(self.session, show, canonical_show)
            return [result for show in shows for result in handler.import_results(show)]

        _cache = self._download_show_files_and_children(show_key)
        results: list[URLImportResult] = []
        for source in self.title_sources(show_key):
            show = self.upsert_show(source, show_key, canonical_show, force=force)
            # The title the first listing was found to be linked to is the title
            # the rest of them are linked to too, so it is handed to them rather
            # than searched for once for each way of watching the same title.
            canonical_show = canonical_show or _canonical_show(show)
            results += handler.import_results(show)
        return results


# TODO: Validate
def _canonical_show(show: Show) -> Show | None:
    """Return the title `show` was found to be linked to, where there is one."""
    if show.canonical_shows:
        return show.canonical_shows[0]
    return None
