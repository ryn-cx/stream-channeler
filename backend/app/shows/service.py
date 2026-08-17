# TODO: Validate
"""Which canonical show a show is linked to, and the settling of it."""

import uuid
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app.canonical_media.service import add_canonical_show
from app.episodes.linker import EpisodeLinker
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
    EpisodeLinker(session, show).link_show()


# TODO: Validate
def set_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> Show:
    """Add the canonical show a `User` chose to what `show` already stands for.

    A website files two shows under one page often enough - a YouTube channel
    whose uploads are two series, a service selling a sequel as another season -
    that a title chosen by hand goes on beside whatever is already there rather
    than over it. Taking one off is `unset_canonical_show`, which is a thing to
    ask for rather than something choosing does quietly.

    The choice is locked, which is what stops the next import searching for a
    title of its own and overruling it. The episodes are read again afterwards,
    since the title just added holds episodes none of them has been read against.
    """
    if show.non_canonical_shows:
        message = "A show other shows are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    add_canonical_show(session, show, canonical_show)
    show.canonical_show_locked = True
    session.add(show)

    EpisodeLinker(session, show).link_show()
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def unset_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> Show:
    """Take `canonical_show` off what `show` stands for.

    Every episode that stood for an episode of the title being taken off is left
    standing for nothing, hand-settled or not: it was settled against a title
    this row has now been said not to be of. What the rest of the episodes are of
    is worked out afresh against the titles that are left.

    The lock stays as it was. An admin saying this row is not that title has
    settled something whether or not another title is named in its place, and an
    import searching for one afresh would only put the same guess back.
    """
    for link in list(show.canonical_show_links):
        if link.canonical_show_id == canonical_show.id:
            session.delete(link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are settled against.
    session.expire(show, ["canonical_show_links"])

    _unlink_unlisted_episodes(session, show)
    EpisodeLinker(session, show).link_show()
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def _unlink_unlisted_episodes(session: Session, show: Show) -> None:
    """Take every episode of `show` off a record no linked title holds."""
    canonical_show_ids = {linked.id for linked in show.canonical_shows}
    for season in show.active_children:
        for episode in season.active_children:
            for link in list(episode.canonical_episode_links):
                if link.canonical_episode.season.show_id in canonical_show_ids:
                    continue
                session.delete(link)
            session.flush()
            session.expire(episode, ["canonical_episode_links"])

            if not episode.canonical_episode_links:
                episode.is_canonical = True
                episode.canonical_episode_locked = False
                episode.canonical_episode_note = None
                session.add(episode)
    session.flush()


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
def update_show_extra(
    session: Session,
    show: Show,
    extra: dict[str, Any] | None,
) -> None:
    """Store `extra` on `show`, and read the title again where the order changed.

    The one way of setting what a plugin keeps about a title, so that whatever
    setting it has to drag along happens wherever it is set from.

    Changing the episode order is the case that drags something along. The order
    decides which season an episode sits in and what it is numbered, and a copy
    is matched to an episode by exactly those, so a link made under the old order
    was made against numbering that no longer exists. The title is read again so
    the new order is written down, and then every copy of it is matched afresh.

    Only the links nobody settled are dropped. One a `User` locked was decided by
    hand and is no more wrong under one order than another.
    """
    validate_extra(session, show, extra)

    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB.episode_groups import chosen_group_id  # noqa: PLC0415

    reordered = chosen_group_id(show.extra) != chosen_group_id(extra)
    show.extra = extra or {}
    session.add(show)

    if reordered:
        _reread_in_new_order(session, show)
        _relink_copies(session, show)
    session.commit()


# TODO: Validate
def update_show_episode_group(
    session: Session,
    show: Show,
    group_id: str | None,
) -> None:
    """Read `show` in the episode order `group_id` names, or in its own for none."""
    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB.episode_groups import dump_extra  # noqa: PLC0415

    update_show_extra(session, show, dump_extra(group_id))


# TODO: Validate
def _reread_in_new_order(session: Session, show: Show) -> None:
    """Read `show` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    TMDB(session).update_show(show, force=True)


# TODO: Validate
def _relink_copies(session: Session, canonical_show: Show) -> None:
    """Match every copy of `canonical_show` against it again."""
    for link in list(canonical_show.non_canonical_shows):
        copy = link.show
        for season in copy.active_children:
            for episode in season.active_children:
                if episode.canonical_episode_locked:
                    continue
                for episode_link in list(episode.canonical_episode_links):
                    session.delete(episode_link)
                episode.is_canonical = True
                episode.canonical_episode_note = None
            session.flush()
        EpisodeLinker(session, copy).link_show()


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
