from __future__ import annotations

from typing import TYPE_CHECKING

from app.canonical_media.keys import tmdb_show_key
from app.media.media_type import TMDBMediaType
from plugins.TMDB.base import TMDBBase
from plugins.TMDB.importer import TMDBImporter
from plugins.TMDB.initialize import TMDBInitializer
from plugins.TMDB.urls import media_url
from plugins.TMDB.utils import first_search_result
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from app.shows.models import Show


class TMDB(TMDBBase, AbstractPlugin, register=True):
    initializer = TMDBInitializer
    importer = TMDBImporter

    def import_search(
        self,
        title: str,
        media_type: TMDBMediaType | None = None,
        year: int | None = None,
    ) -> Show | None:
        """Import the first matching title found via search."""
        search_result = first_search_result(self, title, media_type, year)
        if not search_result:
            return None

        media_type, tmdb_key = search_result
        if media_type == TMDBMediaType.movie:
            return self.import_movie(tmdb_key)
        return self.import_show(tmdb_key)

    def import_show(self, tmdb_id: int) -> Show:
        """Import a TMDB tv entry by its tmdb_id."""
        self.import_url(media_url(TMDBMediaType.tv, tmdb_id))
        # TODO: This isn't ideal as it requires an extra query.
        return self._preload_show(tmdb_show_key(TMDBMediaType.tv, tmdb_id)).one()

    def import_movie(self, tmdb_id: int) -> Show:
        """Import a TMDB movie entry by its tmdb_id."""
        self.import_url(media_url(TMDBMediaType.movie, tmdb_id))
        # TODO: This isn't ideal as it requires an extra query.
        return self._preload_show(tmdb_show_key(TMDBMediaType.movie, tmdb_id)).one()
