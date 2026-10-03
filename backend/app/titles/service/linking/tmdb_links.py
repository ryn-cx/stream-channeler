# TODO: Validate

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.channels.models import ChannelTitle
from app.episodes.models import is_manual_note
from app.plugins.identifiers import TMDB_SOURCE_KEY
from app.titles.models import Title, TitleTmdbTitle
from app.titles.service.linking.episode_relinking import _relink_episode


# TODO: Validate
def _remove_unmatched_for_plugin(
    session: Session,
    title: Title,
    tmdb_title: Title,
) -> None:
    from app.titles.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_titles,
    )

    remove_plugin_unmatched_titles(session, tmdb_title.id, title.source.plugin.key)


# TODO: Validate
def link_unlinked_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleTmdbTitle:
    """Link an unlinked title to a TMDB title and update all channels containing it.

    Channels that include the unlinked title will have it replaced with the TMDB
    title."""
    channel_titles = session.exec(
        select(ChannelTitle).where(
            ChannelTitle.tmdb_title_id == title.id,
        ),
    ).all()
    channel_titles_by_channel_id = {
        channel_title.channel_id: channel_title for channel_title in channel_titles
    }
    channels_with_title_and_tmdb_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                col(ChannelTitle.tmdb_title_id) == tmdb_title.id,
                col(ChannelTitle.channel_id).in_(
                    list(channel_titles_by_channel_id),
                ),
            ),
        ).all(),
    )

    # Replace the unlinked title with the TMDB title.
    for channel_id, channel_title in channel_titles_by_channel_id.items():
        if channel_id in channels_with_title_and_tmdb_title:
            continue
        session.add(
            ChannelTitle(
                channel_id=channel_id,
                tmdb_title_id=tmdb_title.id,
                imported_title_id=channel_title.imported_title_id,
                is_whitelist=channel_title.is_whitelist,
                is_blacklist_only=channel_title.is_blacklist_only,
            ),
        )

    # Remove the unlinked title from all channels.
    for channel_title in channel_titles:
        session.delete(channel_title)
    session.flush()

    existing_link = session.exec(
        select(TitleTmdbTitle).where(
            col(TitleTmdbTitle.title_id) == title.id,
            col(TitleTmdbTitle.tmdb_title_id) == tmdb_title.id,
        ),
    ).first()
    link = existing_link or TitleTmdbTitle(
        title_id=title.id,
        tmdb_title_id=tmdb_title.id,
        note=note,
        manual_tmdb_link=is_manual_note(note),
    )
    session.add(link)
    session.flush()
    _remove_unmatched_for_plugin(session, title, tmdb_title)
    session.expire(title, ["tmdb_title_links", "is_linked"])
    _relink_episode(session, title)
    return link


# TODO: Validate
def _old_validate_titles(title: Title, tmdb_title: Title) -> None:
    """Validate that `title` and `tmdb_title` can be linked.

    The title cannot have any other canonical titles linked to it and it cannot be a TMDB
    title.

    The TMDB title must be canonical TMDB title."""
    if tmdb_title.is_linked:
        message = f"{tmdb_title} is not a canonical title."
        raise ValueError(message)
    if tmdb_title.source.key != TMDB_SOURCE_KEY:
        message = f"{tmdb_title} is not a TMDB title."
        raise ValueError(message)
    if title.source.key == TMDB_SOURCE_KEY:
        message = f"{title} is a TMDB title."
        raise ValueError(message)
    if title.linked_title_links:
        message = f"{title} has other titles linked to it."
        raise ValueError(message)


# TODO: Validate
def old_link_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleTmdbTitle:
    """Link a title to TMDB then links the title's episodes to TMDB.

    Will not remove any existing title links."""
    if tmdb_title.deleted_at is not None:
        message = f"{tmdb_title.name} has been deleted from TMDB."
        raise HTTPException(status_code=409, detail=message)
    _old_validate_titles(title, tmdb_title)
    if not title.is_linked:
        return link_unlinked_title_to_tmdb(session, title, tmdb_title, note)

    _remove_unmatched_for_plugin(session, title, tmdb_title)
    for tmdb_link in title.tmdb_title_links:
        if tmdb_link.tmdb_title_id == tmdb_title.id:
            return tmdb_link

    link = TitleTmdbTitle(
        title_id=title.id,
        tmdb_title_id=tmdb_title.id,
        note=note,
        manual_tmdb_link=is_manual_note(note),
    )
    session.add(link)
    session.flush()
    session.expire(title, ["tmdb_title_links", "is_linked"])
    _relink_episode(session, title)
    return link
