# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

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
from app.titles.models import Title
from app.titles.schemas import (
    TmdbEpisodeGroupOption,
)
from app.titles.service.canonical import match_title_to_tmdb
from app.titles.service.relinking import (
    _relink_non_canonical_titles,
    _reread_in_new_order,
)
from plugins.TMDB import TMDB


# TODO: Validate
def list_tmdb_episode_groups(
    session: Session,
    title: Title,
) -> list[TmdbEpisodeGroupOption]:
    """Return the episode orders TMDB holds for `title`, for one to be chosen from.

    Its own endpoint rather than part of reading the title, because it is read off
    a downloaded file and only ever wanted by somebody about to choose an order.
    A row that is not a TMDB series has none, which reads as an empty list rather
    than as an error: there is nothing wrong with a title having no other order.
    """
    if title.source.plugin.key != TMDB_PLUGIN_KEY:
        return []

    media_type, tmdb_id = get_media_type_and_tmdb_id(title.key)
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
def update_title_extra(
    session: Session,
    title: Title,
    extra: dict[str, Any] | None,
) -> None:
    """Store `extra` on `title`, and read the title again where the order changed.

    The one way of setting what a plugin keeps about a title, so that whatever
    setting it has to drag along happens wherever it is set from.

    Changing the episode order is the case that drags something along. The order decides
    which season an episode sits in and what it is numbered, and a non-canonical row is
    matched to an episode by exactly those. The title is read again so the new order is
    written down.
    """
    validate_extra(session, title, extra)

    reordered = chosen_group_id(title.extra) != chosen_group_id(extra)
    title.extra = extra or {}
    session.add(title)

    if reordered:
        _reread_in_new_order(session, title)
        _relink_non_canonical_titles(session, title)
    session.commit()


# TODO: Validate
def update_title_episode_group(
    session: Session,
    title: Title,
    group_id: str | None,
) -> None:
    """Read `title` in the episode order `group_id` names, or in its own for none."""
    update_title_extra(session, title, dump_extra(group_id))


# TODO: Validate
def force_update_title(session: Session, title: Title) -> Title:
    from plugins.utils.manage_plugins import import_plugins, plugins  # noqa: PLC0415

    import_plugins()
    plugin_classes = {plugin.plugin_name(): plugin for plugin in plugins}
    plugin_class = plugin_classes.get(title.source.plugin.key)
    if plugin_class is None:
        message = (
            f"No plugin named {title.source.plugin.key!r} to read the title again."
        )
        raise HTTPException(status_code=422, detail=message)

    plugin_instance = plugin_class(session, title.source.plugin)
    plugin_instance.update_title(title, force=True)
    match_title_to_tmdb(session, title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def validate_extra(
    session: Session,
    title: Title,
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
    if title.source.plugin.key != TMDB_PLUGIN_KEY:
        return

    group_id = chosen_group_id(extra)
    if group_id is None:
        return

    media_type, tmdb_id = get_media_type_and_tmdb_id(title.key)
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
        message = f"TMDB holds no episode order {group_id!r} for this title."
        raise HTTPException(status_code=422, detail=message)
