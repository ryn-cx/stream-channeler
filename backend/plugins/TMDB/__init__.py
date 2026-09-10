# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.canonical_media.tmdb import (
    get_media_type_and_tmdb_id,
)
from app.media.media_type import TMDBMediaType
from plugins.TMDB.constants import MOVIE_URL_REGEX, TV_URL_REGEX
from plugins.TMDB.importer import TMDBImporter, TMDBMovie, TMDBSeries
from plugins.TMDB.shared import TMDBShared
from plugins.TMDB.utils import Provider, tmdb_url
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    MediaNotFoundError,
    URLImportResult,
)

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class TMDB(TMDBShared, AbstractPlugin, register=False):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

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
        if not search_result:
            msg = f"Could not find {name} on {self.plugin_name()}."
            raise MediaNotFoundError(msg)

        found_media_type, tmdb_media_id = search_result
        media_importer = self._get_media_importer_from_media_type(found_media_type)
        return media_importer.import_url(tmdb_url(found_media_type, tmdb_media_id))
