# TODO: Validate
from __future__ import annotations

from typing import override

from bs4 import Tag

from plugins.TMDB.files import TMDB_DOMAIN, TitlePage
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import TMDBURLHandler
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class ImportURLMixin(
    UpsertMixin,
    URLHandlerPlugin[TMDBURLHandler],
    register=False,
):
    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN

    @override
    def import_url(self, url: str, tmdb_id: int | None = None) -> list[URLImportResult]:
        """Import the title the URL names from wherever it can be watched.

        TMDB streams nothing itself, so the page is read for the JustWatch link
        it lists and the import is handed off to the service the title is on. A
        title JustWatch does not carry is imported as this plugin's own media
        instead, which is all there is to serve for it.
        """
        self._use_tmdb_id(tmdb_id)
        handler = self._get_url_handler(url)
        handler.raise_if_invalid()

        justwatch_url = self._justwatch_url(handler.title_page_file())
        if justwatch_url is None:
            return handler.import_results(self._import_show(handler.show_key))

        # Imported lazily because JustWatch's files use this plugin to resolve
        # TMDB ids, so importing it up here would be circular.
        from plugins.JustWatch import JustWatch  # noqa: PLC0415

        return JustWatch(self.session).import_url(justwatch_url, handler.tmdb_id)

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
