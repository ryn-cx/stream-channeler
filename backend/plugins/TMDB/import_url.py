# TODO: Validate
"""Reading a title in, whether a URL named it or an id did."""

from __future__ import annotations

import re
from typing import Any, override

from app.canonical_media.keys import (
    tmdb_show_key,
)
from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.TMDB.base import TMDBBase
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v2.files import BaseFile
from plugins.utils.base_plugin_v2.workers import URLImporter

# from plugins.WatchMode import WatchMode  # noqa: ERA001


# TODO: Validate
def _title_url_regex(media_type: MediaType) -> str:
    return rf"\/{media_type}\/(?P<{media_type}_tmdb_id>\d+)"


# TODO: Validate
class TMDBImportURL(URLImporter, TMDBBase):
    _MOVIE_URL_REGEX = _title_url_regex(MediaType.movie)
    _TV_URL_REGEX = _title_url_regex(MediaType.tv)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._TV_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        for media_type, url_regex in (
            (MediaType.movie, self._MOVIE_URL_REGEX),
            (MediaType.tv, self._TV_URL_REGEX),
        ):
            if match := re.match(domain_regex + url_regex, url):
                tmdb_id = int(match.group(f"{media_type}_tmdb_id"))
                self._show_key = tmdb_show_key(media_type, tmdb_id)
                self.raise_if_invalid_file(
                    self.title_page_file(media_type, tmdb_id),
                    url,
                )
                detail_file: BaseFile[Any]
                if media_type == MediaType.movie:
                    detail_file = self.movie_detail_file(tmdb_id)
                else:
                    detail_file = self.show_detail_file(tmdb_id)
                self.raise_if_invalid_file(detail_file, url)
                return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def import_url(
        self,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = self._show_key
        show_preload = self._preload_show(show_key, preload_episodes=True)
        existing_show = show_preload.one_or_none()
        if not existing_show or force:
            _cache = self._download_show_files_and_children(show_key)
            existing_show = self.upsert_show(self.source, show_key, force=force)

            # This title's own rows are written before anything is handed on. A
            # website's plugin resolves the title it carries by asking TMDB for
            # it, so a hand-off made first would be asking for a title that is
            # not stored yet and would send the import straight back round; made
            # after, that ask is answered by the row written here and the chain
            # ends.
            if canonical_show is None:
                self._import_listed_sources(show_key, existing_show, force=force)

        return self._import_results(existing_show)
