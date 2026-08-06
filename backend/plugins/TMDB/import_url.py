# TODO: Validate
from __future__ import annotations

import re
from typing import override

from bs4 import Tag

from plugins.TMDB.files import TMDB_DOMAIN, FileMixin, TitlePage
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult

_TITLE_PATH_REGEX = r"\/(?P<media_type>movie|tv)\/(?P<tmdb_id>\d+)"


class ImportURLMixin(FileMixin, register=False):
    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN

    @classmethod
    @override
    def url_regex(cls) -> str:
        return cls._domain_regex() + _TITLE_PATH_REGEX

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        """Import a title from its TMDB page by way of JustWatch.

        TMDB tracks where a title can be watched but not how to import it, so
        the page is only used to reach the JustWatch title it links to, which is
        what knows the offers every source has.
        """
        match = re.match(self.url_regex(), url)
        if match is None:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)

        page_file = self.title_page_file(
            match.group("media_type"),
            int(match.group("tmdb_id")),
        )
        page_file.download_if_outdated()
        if not page_file.database_record.content:
            msg = f"Invalid {self.plugin_key()} URL: {url}"
            raise InvalidURLError(msg)

        justwatch_url = self._justwatch_url(page_file)
        if justwatch_url is None:
            msg = f"TMDB has no JustWatch link for {url}"
            raise InvalidURLError(msg)

        # Imported lazily because JustWatch's files use this plugin to resolve
        # TMDB ids, so importing it up here would be circular.
        from plugins.JustWatch import JustWatch  # noqa: PLC0415

        return JustWatch(self.session).import_url(justwatch_url)

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
