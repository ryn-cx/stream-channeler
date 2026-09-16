from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.importer import (
    NetflixImporter,
    NetflixMovieImporter,
    NetflixSeriesImporter,
)
from plugins.Netflix.shared import NetflixShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class Netflix(NetflixShared, AbstractPlugin, register=True):
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    @override
    def _media_importer_from_url(self, url: str) -> NetflixImporter:
        # Movies and series use the same URL format and the same title_file, but the
        # title_file contains the media type information.
        if not (match := re.match(self._domains_regex() + TITLE_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        title_file = self.title_file(match.group("title_key"))
        self.raise_invalid_url_if_no_content(title_file, url)
        if title_file.parsed().field__typename == "Movie":
            return NetflixMovieImporter(self.session, self.plugin, self._file_cache)
        return NetflixSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> list[str]:
        similar_file = self.similar_file(title.key)
        # TODO: This is temporary until all files are downloaded
        similar_file.download_if_outdated()
        return [
            self.title_url(str(similar.video_id))
            for similar in similar_file.parsed().similar_videos
        ]

    @override
    def _media_importer_from_title(self, title: Title) -> NetflixImporter:
        if not title.media_type:  # Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == "Movie":
            return NetflixMovieImporter(self.session, self.plugin, self._file_cache)
        return NetflixSeriesImporter(self.session, self.plugin, self._file_cache)
