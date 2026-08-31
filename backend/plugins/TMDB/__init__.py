# TODO: Validate
"""The Movie Database plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.canonical_media.keys import tmdb_show_key
from app.media.media_type import MediaType
from plugins.TMDB.base import TMDBBase
from plugins.TMDB.constants import media_url
from plugins.TMDB.import_url import TMDBImportURL
from plugins.TMDB.initialize import TMDBInitializer
from plugins.TMDB.update import TMDBUpdater
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class TMDB(TMDBBase, AbstractPlugin, register=True):
    """The Movie Database plugin."""

    initializer = TMDBInitializer
    url_importer = TMDBImportURL
    updater = TMDBUpdater

    # TODO: Validate
    def import_search(
        self,
        name: str,
        media_type: MediaType | None = None,
        year: int | None = None,
        *,
        force: bool = False,
    ) -> Show | None:
        """Import the first title TMDB returns for `name`.

        `media_type` narrows the search to one half of the catalogue and `year`
        to when the title came out. Neither is required: a search of both halves
        takes whichever half the first result turned out to be from.

        Returns None when TMDB has nothing under that name, since a name is a
        guess at a title in a way an id is not.
        """
        found = self._first_search_result(name, media_type, year)
        if found is None:
            return None

        half, tmdb_id = found
        if half == MediaType.movie:
            return self.import_movie(tmdb_id, force=force)
        return self.import_show(tmdb_id, force=force)

    # TODO: Validate
    def _first_search_result(
        self,
        name: str,
        media_type: MediaType | None,
        year: int | None,
    ) -> tuple[MediaType, int] | None:
        """Return which half the first title TMDB returns is from, and its id."""
        if media_type is not None:
            results = self.search_media(media_type, name, year).parsed().results
            return (media_type, results[0].id) if results else None

        # A search of both halves also returns people, who are no title and are
        # passed over rather than taken as the first result.
        for result in self.search_media(None, name, year).parsed().results:
            # Which half of the catalogue a search of both says a result came
            # from. A multi search also returns people, who are no title and
            # cannot be imported.
            half = {"movie": MediaType.movie, "tv": MediaType.tv}.get(
                result.media_type,
            )
            if half is not None:
                return half, result.id
        return None

    # TODO: Validate
    def import_show(self, tmdb_id: int, *, force: bool = False) -> Show:
        """Import a TMDB tv entry using a tmdb_id."""
        self.import_url(media_url(MediaType.tv, tmdb_id), force=force)
        return self._preload_show(tmdb_show_key(MediaType.tv, tmdb_id)).one()

    # TODO: Validate
    def import_movie(self, tmdb_id: int, *, force: bool = False) -> Show:
        """Import a TMDB movie entry using a tmdb_id."""
        self.import_url(media_url(MediaType.movie, tmdb_id), force=force)
        return self._preload_show(tmdb_show_key(MediaType.movie, tmdb_id)).one()
