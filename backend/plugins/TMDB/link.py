# TODO: Validate
"""Working out which TMDB title a listing is.

The canonical linking is a noop for now: nothing is pointed at anything, and
every record stands only for itself. What is left is the lookup a plugin uses to
decide which title an import is working on.
"""

from typing import NamedTuple

from sqlmodel import Session

from app.canonical_media.keys import SHOW_LEVEL, parse_tmdb_key
from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.TMDB import TMDB

_SEARCHED_MEDIA_TYPES = {
    "movie": MediaType.movie,
    "tv": MediaType.tv,
}


# TODO: Validate
class Media(NamedTuple):
    """One title TMDB holds: which half of the catalogue, and its id."""

    media_type: MediaType
    tmdb_id: int


# TODO: Validate
class TMDBLinker:
    """Works out which TMDB title a listing is."""

    # TODO: Validate
    def __init__(self, session: Session) -> None:
        """Build a linker for one session."""
        self.session = session
        self.tmdb = TMDB(session)


    # TODO: Validate
    def search_media(
        self,
        name: str,
        media_type: MediaType | None = None,
        year: int | None = None,
    ) -> Media | None:
        """Return the media TMDB lists under a name, or None.

        Without a `media_type` both halves of the catalogue are searched and the
        best match is taken. A search across both turns up people as well as
        media, and a person is not something to be a copy of.
        """
        if media_type is not None:
            results = (
                self.tmdb.auto_updating_search_media(media_type, name, year)
                .parsed()
                .results
            )
            return Media(media_type, results[0].id) if results else None

        found = self.tmdb.auto_updating_search_media(None, name, year).parsed().results
        return next(
            (
                Media(half, result.id)
                for result in found
                if (half := _SEARCHED_MEDIA_TYPES.get(result.media_type)) is not None
            ),
            None,
        )

    # TODO: Validate
    def known_media(
        self,
        show: Show,  # noqa: ARG002 - Read again once linking is not a noop.
        media_type: MediaType | None = None,
        canonical_show: Show | None = None,
    ) -> Media | None:
        """Return the media this listing is already known to be, or None.

        Only what a caller named, while nothing is linked to read an answer off.
        """
        return self.supplied_media(media_type, canonical_show)

    # TODO: Validate
    @staticmethod
    def supplied_media(
        media_type: MediaType | None,
        canonical_show: Show | None,
    ) -> Media | None:
        """Return the media a caller named, when it is what this listing is.

        A caller naming a title from the other half of TMDB's catalogue is naming
        something else the listing also carries, so the listing still has to find
        its own title for itself.
        """
        if canonical_show is None:
            return None
        parsed = parse_tmdb_key(canonical_show.key, SHOW_LEVEL)
        if parsed is None:
            return None
        supplied = Media(*parsed)
        if media_type is not None and supplied.media_type != media_type:
            return None
        return supplied

    # TODO: Validate
    def title_to_hand_off(
        self,
        media_type: MediaType,
        tmdb_id: int | None,
        canonical_show: Show | None,
    ) -> Show | None:
        """Return the title to tell another plugin about when handing an import on."""
        if canonical_show is not None:
            return canonical_show
        if tmdb_id is None:
            return None
        if media_type == MediaType.movie:
            return self.tmdb.import_movie(tmdb_id)
        return self.tmdb.import_show(tmdb_id)
