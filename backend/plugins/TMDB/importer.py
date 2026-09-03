# TODO: Validate
"""Reading a title in, whether a URL named it or an id did.

A title is read again on a timer, and reading one in full is a file per season
whether anything moved or not. What TMDB's changes endpoints answer is which
records moved, so a read starts by asking that and goes no further than the
records named.
"""

from __future__ import annotations

import re
from typing import Any, override

from app.canonical_media.keys import (
    tmdb_show_key,
)
from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from plugins.TMDB.base import TMDBBase
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v2.files import (
    BaseFile,
)
from plugins.utils.base_plugin_v2.importer import BaseImporter

# from plugins.WatchMode import WatchMode  # noqa: ERA001


# TODO: Validate
def _title_url_regex(media_type: TMDBMediaType) -> str:
    return rf"\/{media_type}\/(?P<{media_type}_tmdb_id>\d+)"


# TODO: Validate
class TMDBImporter(BaseImporter, TMDBBase):
    _MOVIE_URL_REGEX = _title_url_regex(TMDBMediaType.movie)
    _TV_URL_REGEX = _title_url_regex(TMDBMediaType.tv)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._MOVIE_URL_REGEX, cls._TV_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        for media_type, url_regex in (
            (TMDBMediaType.movie, self._MOVIE_URL_REGEX),
            (TMDBMediaType.tv, self._TV_URL_REGEX),
        ):
            if match := re.match(domain_regex + url_regex, url):
                tmdb_id = int(match.group(f"{media_type}_tmdb_id"))
                self.raise_if_invalid_file(
                    self.title_page_file(media_type, tmdb_id),
                    url,
                )
                detail_file: BaseFile[Any]
                if media_type == TMDBMediaType.movie:
                    detail_file = self.movie_detail_file(tmdb_id)
                else:
                    detail_file = self.show_detail_file(tmdb_id)
                self.raise_if_invalid_file(detail_file, url)
                return tmdb_show_key(media_type, tmdb_id)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        # TMDB should always be canonical so if it is imported with a caonical_show
        # something has gone wrong.
        if canonical_show is not None:
            msg = "canonical_show should be None when importing TMDB URLs."
            raise InvalidURLError(msg)

        show_key = self._parse_url(url)
        existing_show = self._preload_show(
            show_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_show:
            _cache = self._download_show_files_and_children(show_key)
            existing_show = self.upsert_show(self.source, show_key)
            self._import_media_from_other_websites(show_key, existing_show)

        return self._import_results(existing_show)
