# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from app.canonical_media.tmdb import (
    chosen_group_id,
    dump_extra,
    get_media_type_and_tmdb_id,
)
from app.media.media_type import TMDBMediaType
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.shows.models import Show
from app.shows.schemas import (
    TmdbEpisodeGroupOption,
)
from app.shows.service.canonical import match_show_to_tmdb
from app.shows.service.relinking import (
    _relink_non_canonical_shows,
    _reread_in_new_order,
)
from plugins.TMDB import TMDB


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

    media_type, tmdb_id = get_media_type_and_tmdb_id(show.key)
    if media_type is not TMDBMediaType.tv:
        return []

    groups_file = TMDB(session).tv_series_episode_groups_file(tmdb_id)
    if not groups_file.database_record.content:
        return []

    return [
        TmdbEpisodeGroupOption(
            id=group.id,
            name=group.name,
            description=group.description,
            group_count=group.group_count,
            episode_count=group.episode_count,
            type=group.type,
        )
        for group in groups_file.parsed().results
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

    Changing the episode order is the case that drags something along. The order decides
    which season an episode sits in and what it is numbered, and a non-canonical row is
    matched to an episode by exactly those. The title is read again so the new order is
    written down.
    """
    validate_extra(session, show, extra)

    reordered = chosen_group_id(show.extra) != chosen_group_id(extra)
    show.extra = extra or {}
    session.add(show)

    if reordered:
        _reread_in_new_order(session, show)
        _relink_non_canonical_shows(session, show)
    session.commit()


# TODO: Validate
def update_show_episode_group(
    session: Session,
    show: Show,
    group_id: str | None,
) -> None:
    """Read `show` in the episode order `group_id` names, or in its own for none."""
    update_show_extra(session, show, dump_extra(group_id))


# TODO: Validate
def force_update_show(session: Session, show: Show) -> Show:
    from plugins.utils.manage_plugins import import_plugins, plugins  # noqa: PLC0415

    import_plugins()
    plugin_classes = {plugin.plugin_name(): plugin for plugin in plugins}
    plugin_class = plugin_classes.get(show.source.plugin.key)
    if plugin_class is None:
        message = f"No plugin named {show.source.plugin.key!r} to read the show again."
        raise HTTPException(status_code=422, detail=message)

    plugin_instance = plugin_class(session, show.source.plugin)
    plugin_instance.update_show(show, force=True)
    match_show_to_tmdb(session, show)
    session.commit()
    session.refresh(show)
    return show


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

    group_id = chosen_group_id(extra)
    if group_id is None:
        return

    media_type, tmdb_id = get_media_type_and_tmdb_id(show.key)
    if media_type is not TMDBMediaType.tv:
        message = "A film has no episode orders to be read in."
        raise HTTPException(status_code=422, detail=message)

    groups_file = TMDB(session).tv_series_episode_groups_file(tmdb_id)
    known = (
        {group.id for group in groups_file.parsed().results}
        if groups_file.database_record.content
        else set()
    )
    if group_id not in known:
        message = f"TMDB holds no episode order {group_id!r} for this show."
        raise HTTPException(status_code=422, detail=message)
