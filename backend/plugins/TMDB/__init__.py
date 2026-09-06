# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.canonical_media.tmdb import (
    get_media_type_and_tmdb_id,
)
from app.media.media_type import TMDBMediaType
from plugins.TMDB.importer import TMDBImporter, TMDBMovie, TMDBSeries
from plugins.TMDB.shared import (
    MOVIE_URL_REGEX,
    TV_URL_REGEX,
    TMDBShared,
)
from plugins.TMDB.utils import tiel_url
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    MediaNotFoundError,
    URLImportResult,
)
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class TMDBInitializer(BasePluginInitializer, TMDBShared):
    """Class for initializing TMDB's database entries."""


# TODO: Validate
class TMDB(TMDBShared, BaseReadURL, AbstractPlugin, register=True):
    initializer = TMDBInitializer

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
            return TMDBMovie(self)
        return TMDBSeries(self)

    # TODO: Validate
    @override
    def _get_media_importer_from_url(self, url: str) -> TMDBImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return TMDBMovie(self)
        if re.match(domain_regex + TV_URL_REGEX, url):
            return TMDBSeries(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _get_media_importer_from_title(self, title: Title) -> TMDBImporter:
        media_type, _ = get_media_type_and_tmdb_id(title.key)
        return self._get_media_importer_from_media_type(media_type)

    # TODO: Validate
    @override
    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType | None = None,
        year: int | None = None,
    ) -> list[URLImportResult]:
        search_result = self.first_search_result(names[0], media_type, year)
        if not search_result:
            msg = f"Could not find {names[0]} on {self.plugin_name()}."
            raise MediaNotFoundError(msg)

        found_media_type, tmdb_media_id = search_result
        medai_importer = self._get_media_importer_from_media_type(found_media_type)
        return medai_importer.import_url(tiel_url(found_media_type, tmdb_media_id))
