# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from app.tmdb_media.tmdb import (
    get_media_type_and_tmdb_id,
    tmdb_title_key,
)
from plugins.TMDB.constants import MOVIE_URL_REGEX, TV_URL_REGEX
from plugins.TMDB.importer import TMDBImporter, TMDBMovie, TMDBSeries
from plugins.TMDB.shared import TMDBShared
from plugins.TMDB.utils import Provider, tmdb_url
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    MediaNotFoundError,
    URLImportResult,
)

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class TMDB(TMDBShared, AbstractPlugin, register=True):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

    # TODO: Validate
    @override
    def title_key_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            return tmdb_title_key(TMDBMediaType.movie, int(match.group("title_key")))
        if match := re.match(domain_regex + TV_URL_REGEX, url):
            return tmdb_title_key(TMDBMediaType.tv, int(match.group("title_key")))

        msg = f"No title key in {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _get_media_importer_from_media_type(
        self,
        media_type: TMDBMediaType,
    ) -> TMDBImporter:
        if media_type == TMDBMediaType.movie:
            return TMDBMovie(self.session, self.plugin, self._file_cache)
        return TMDBSeries(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> TMDBImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return TMDBMovie(self.session, self.plugin, self._file_cache)
        return TMDBSeries(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> TMDBImporter:
        media_type, _ = get_media_type_and_tmdb_id(title.key)
        return self._get_media_importer_from_media_type(media_type)

    # TODO: Validate
    def streaming_providers(self, title: Title) -> list[Provider]:
        return self._media_importer_from_title(title).streaming_providers(title.key)

    # TODO: Validate
    @override
    def import_search(
        self,
        name: str,
        media_type: TMDBMediaType | None = None,
        year: int | None = None,
    ) -> list[URLImportResult]:
        search_result = self.first_search_result(name, media_type, year)
        if search_result:
            found_media_type, tmdb_media_id = search_result
            media_importer = self._get_media_importer_from_media_type(found_media_type)
            return media_importer.import_url(tmdb_url(found_media_type, tmdb_media_id))
        return []
