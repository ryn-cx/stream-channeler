# TODO: Validate
"""The Movie Database plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.canonical_media.keys import tmdb_show_key
from app.media.media_type import TMDBMediaType
from plugins.TMDB.base import TMDBBase
from plugins.TMDB.importer import TMDBImporter
from plugins.TMDB.initialize import TMDBInitializer
from plugins.TMDB.urls import media_url
from plugins.TMDB.utils import first_search_result
from plugins.utils.abstract_plugin import AbstractPlugin, TMDBLookupInfo

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class TMDB(TMDBBase, AbstractPlugin, register=True):
    """The Movie Database plugin."""

    initializer = TMDBInitializer
    importer = TMDBImporter

    # TODO: Validate
    def import_search(self, lookup_info: TMDBLookupInfo) -> Show | None:
        """Import the first title TMDB returns for a show another plugin names.

        Returns None when TMDB has nothing under that name, since a name is a
        guess at a title in a way an id is not.
        """
        found = first_search_result(
            self,
            lookup_info.title,
            lookup_info.media_type,
            lookup_info.year,
        )
        if found is None:
            return None

        half, tmdb_id = found
        if half == TMDBMediaType.movie:
            return self.import_movie(tmdb_id)
        return self.import_show(tmdb_id)

    # TODO: Validate
    def import_show(self, tmdb_id: int) -> Show:
        """Import a TMDB tv entry using a tmdb_id."""
        self.import_url(media_url(TMDBMediaType.tv, tmdb_id))
        return self._preload_show(tmdb_show_key(TMDBMediaType.tv, tmdb_id)).one()

    # TODO: Validate
    def import_movie(self, tmdb_id: int) -> Show:
        """Import a TMDB movie entry using a tmdb_id."""
        self.import_url(media_url(TMDBMediaType.movie, tmdb_id))
        return self._preload_show(tmdb_show_key(TMDBMediaType.movie, tmdb_id)).one()
