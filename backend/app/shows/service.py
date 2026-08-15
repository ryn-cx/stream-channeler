# TODO: Validate
"""Which canonical show a show is linked to, and the settling of it."""

import uuid

from sqlmodel import Session

from app.canonical_media.service import add_canonical_show
from app.episodes.service import EpisodeLinker
from app.media.media_type import MediaType
from app.shows.models import Show

_TMDB_MEDIA_TYPES = {
    "Movie": MediaType.movie,
    "Series": MediaType.tv,
    "TV Show": MediaType.tv,
}
"""Which TMDB media type each of a show's own media types is searched under.

A media type TMDB has no half of - a channel, a video, a concert - is not
searched for at all.
"""

_LOOKUPS_IN_FLIGHT = "canonical_show_lookups"
"""Where a session keeps the shows it is in the middle of searching for."""


# TODO: Validate
def find_and_add_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show | None = None,
) -> None:
    """Link `show` to the canonical show it is a copy of, and read its episodes.

    A show TMDB has no match for is the canonical show, which is what it already
    is when it is written, so there is nothing to do for it here. One TMDB does
    have a match for is linked to that match, and `add_canonical_show` is what
    makes it non-canonical.

    A show already linked to a canonical show is left alone, since that may have
    been settled by hand and writing the show again is no reason to overrule it.
    A show linked to nothing is searched for afresh every time it is written,
    since a match that was not there to be found when it was first written can be
    there now.

    The episodes are read against the canonical show whether or not one was found
    here, because the episodes just written include ones the canonical show it is
    already linked to has never been read against.
    """
    if not (canonical_show or show.canonical_shows):
        canonical_show = _searched_show(session, show)
    if canonical_show:
        add_canonical_show(session, show, canonical_show)
    EpisodeLinker(session, show).link()


# TODO: Validate
def _searched_show(session: Session, show: Show) -> Show | None:
    """Return the TMDB show matching this show's own name, where there is one.

    Searched on the show's own name, year and media type rather than on anything
    only its source could answer, so every show is searched the same way and one
    with no name is not searched at all.
    """
    media_type = _TMDB_MEDIA_TYPES.get(show.media_type or "")
    if media_type is None or not show.name:
        return None

    # Held for as long as the search runs, because finding a match imports it and
    # importing it writes shows, which is what asks for a match again.
    in_flight: set[uuid.UUID] = session.info.setdefault(_LOOKUPS_IN_FLIGHT, set())
    if show.id in in_flight:
        return None
    in_flight.add(show.id)
    try:
        # Imported here rather than at the top of the module because the plugin
        # is built on the base every plugin is, which reads this module in turn.
        from plugins.TMDB import TMDB  # noqa: PLC0415

        return TMDB(session).import_search(show.name, media_type, show.year)
    finally:
        in_flight.discard(show.id)
