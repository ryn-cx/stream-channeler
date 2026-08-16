# TODO: Validate
"""Which canonical show a show is linked to, and the settling of it."""

import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app.canonical_media.service import add_canonical_show
from app.episodes.service import EpisodeLinker
from app.media.identifiers import TMDB_PLUGIN_KEY
from app.media.media_type import MediaType
from app.shows.models import Show
from app.shows.schemas import TmdbEpisodeGroupOption

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
def list_tmdb_episode_groups(
    session: Session,
    show: Show,
) -> list[TmdbEpisodeGroupOption]:
    """Return the episode orders TMDB holds for `show`, for one to be chosen from.

    Its own endpoint rather than part of reading the show, because it is read off
    a downloaded file and only ever wanted by somebody about to choose an order.
    A row that is not a TMDB series has none, which reads as an empty list rather
    than as an error: there is nothing wrong with a title having no other order.
    """
    if show.source.plugin.key != TMDB_PLUGIN_KEY:
        return []

    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB import TMDB  # noqa: PLC0415
    from plugins.TMDB.keys import parse_show_key  # noqa: PLC0415

    media_type, tmdb_id = parse_show_key(show.key)
    if media_type is not MediaType.tv:
        return []

    groups = TMDB(session).episode_groups_file(tmdb_id).parsed()
    return [
        TmdbEpisodeGroupOption(
            id=group.id,
            name=group.name,
            description=group.description,
            group_count=group.group_count,
            episode_count=group.episode_count,
            type=group.type,
        )
        for group in groups.results
    ]


# TODO: Validate
def validate_extra(
    session: Session,
    show: Show,
    extra: dict[str, Any] | None,
) -> None:
    """Raise where `extra` names an episode order TMDB has no record of.

    Choosing an order replaces the title's own seasons with that order's groups,
    so an id naming nothing would leave the title with no seasons at all. The
    check is against the orders TMDB actually holds for this title rather than
    against the shape of the id, since an id that reads right and names another
    title's order is just as empty.

    Only TMDB's own rows carry an order, so a row of any other plugin is left
    alone: `extra` is each plugin's own scratch column and nothing here knows
    what another plugin keeps in it.
    """
    if show.source.plugin.key != TMDB_PLUGIN_KEY:
        return

    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB import TMDB  # noqa: PLC0415
    from plugins.TMDB.episode_groups import chosen_group_id  # noqa: PLC0415
    from plugins.TMDB.keys import parse_show_key  # noqa: PLC0415

    group_id = chosen_group_id(extra)
    if group_id is None:
        return

    media_type, tmdb_id = parse_show_key(show.key)
    if media_type is not MediaType.tv:
        message = "A film has no episode orders to be read in."
        raise HTTPException(status_code=422, detail=message)

    groups = TMDB(session).episode_groups_file(tmdb_id).parsed()
    known = {group.id for group in groups.results}
    if group_id not in known:
        message = f"TMDB holds no episode order {group_id!r} for this show."
        raise HTTPException(status_code=422, detail=message)


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
