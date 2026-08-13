# TODO: Validate
from __future__ import annotations

from typing import override

from bs4 import Tag

from app.shows.models import Show
from plugins.TMDB.files import TMDB_DOMAIN, TitlePage
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import TMDBURLHandler
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class ImportURLMixin(
    UpsertMixin,
    URLHandlerPlugin[TMDBURLHandler],
    register=False,
):
    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        handler = self.get_url_handler(url)
        handler.raise_if_invalid()

        # The title itself is read into the canonical tables, which is all TMDB
        # has to contribute; where it can be watched is JustWatch's to say, and
        # its results are what the channel takes on.
        title = self.import_title(handler.media_type, handler.tmdb_id)

        justwatch_url = self._justwatch_url(handler.title_page_file())
        if justwatch_url is None:
            return []

        # Imported lazily because JustWatch's files use this plugin to resolve
        # TMDB ids, so importing it up here would be circular.
        from plugins.JustWatch import JustWatch  # noqa: PLC0415

        # The row rather than the id, since the URL names the title outright and
        # a listing further down can be a copy of it without being chiefly of it.
        return JustWatch(self.session).import_url(justwatch_url, title)

    # TODO: Validate
    @staticmethod
    def _justwatch_url(page_file: TitlePage) -> str | None:
        """Return the JustWatch link TMDB lists among a title's social links."""
        for link in page_file.parsed().select("a.social_link[href]"):
            if not isinstance(link, Tag):
                continue
            href = str(link["href"])
            if "justwatch.com" in href:
                return href
        return None
