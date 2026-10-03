# TODO: Validate

import re

from fastapi import HTTPException
from sqlmodel import Session, select

from app.episodes.models import MANUAL_NOTE_PREFIX
from app.titles.models import Title
from app.titles.service.linking.channel_moves import (
    _move_imported_channel_titles,
    _old_move_channel_titles_to_title,
)
from app.titles.service.linking.episode_relinking import (
    _old_relink_episodes,
    _old_unlink_episodes_from_dropped_tmdb_titles,
    _relink_episode,
)
from app.titles.service.linking.tmdb_links import old_link_title_to_tmdb
from app.tmdb_media.filters import is_not_linked
from app.utils import tz_datetime

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def old_relink_title(session: Session, title: Title) -> Title:
    if not title.is_linked:
        _old_relink_episodes(session, title)
    else:
        _relink_episode(session, title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def old_link_title_to_tmdb_title(
    session: Session,
    website_title: Title,
    tmdb_title: Title,
) -> Title:
    if website_title.linked_title_links:
        message = "A title other titles are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    old_link_title_to_tmdb(
        session,
        website_title,
        tmdb_title,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    website_title.tmdb_title_validated_at = tz_datetime.now()
    website_title.tmdb_absent_at = None
    session.add(website_title)

    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def tmdb_title_from_url(session: Session, tmdb_url: str) -> Title:
    from plugins.TMDB import TMDB  # noqa: PLC0415

    stripped_url = tmdb_url.strip()
    if not _TMDB_TITLE_URL.search(stripped_url):
        raise HTTPException(
            status_code=400,
            detail=f"{tmdb_url} is not the address of a TMDB film or series",
        )

    imported_titles = TMDB(session).validate_and_import_url(stripped_url)
    return session.exec(
        select(Title).where(
            is_not_linked(Title),
            Title.key == imported_titles[0].title.key,
        ),
    ).one()


# TODO: Validate
def old_link_title_to_tmdb_title_from_url(
    session: Session,
    website_title: Title,
    tmdb_url: str,
) -> Title:
    """Import the TMDB title at `tmdb_url` and link `website_title` to it."""
    tmdb_title = tmdb_title_from_url(session, tmdb_url)
    return old_link_title_to_tmdb_title(session, website_title, tmdb_title)


# TODO: Validate
def old_import_linked_title_from_url(
    session: Session,
    tmdb_title: Title,
    title_url: str,
) -> Title:
    """Import the title at `title_url` and link it to `tmdb_title`."""
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import get_plugin_from_url  # noqa: PLC0415

    stripped_url = title_url.strip()
    if tmdb_title.is_linked:
        message = "A title linked to a canonical title cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = get_plugin_from_url(stripped_url)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {stripped_url}")

    plugin_instance = plugin_class(session)
    try:
        import_results = plugin_instance.validate_and_import_url(stripped_url)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for import_result in import_results:
        old_link_title_to_tmdb(
            session,
            import_result.title,
            tmdb_title,
            "Automatic: Import match",
        )

    session.flush()
    session.expire(tmdb_title, ["linked_title_links"])
    imported_title_keys = {import_result.title.key for import_result in import_results}
    for linked_title_link in tmdb_title.linked_title_links:
        linked_title = linked_title_link.linked_title
        if linked_title.key not in imported_title_keys:
            continue
        linked_title.tmdb_title_validated_at = tz_datetime.now()
        linked_title.tmdb_absent_at = None
        linked_title_link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        linked_title_link.manual_tmdb_link = True
        session.add(linked_title)
        session.add(linked_title_link)

    session.commit()
    session.refresh(tmdb_title)
    return tmdb_title


# TODO: Validate
def _lock_title_links(session: Session, title: Title) -> None:
    title.link_status = "Linked" if title.tmdb_title_links else "No Match Found"
    title.tmdb_title_validated_at = tz_datetime.now()
    title.tmdb_absent_at = None
    session.add(title)


# TODO: Validate
def mark_title_absent_from_tmdb(session: Session, title: Title) -> Title:
    """Settle a `Title` as one TMDB has no record of.

    Every canonical title it stands for is dropped, so what is left is a row
    standing only for itself, locked so no later import links it again.
    """
    if title.tmdb_title_links:
        old_make_title_unlinked(session, title)

    now = tz_datetime.now()
    title.link_status = "No Match Found"
    title.tmdb_title_validated_at = now
    title.tmdb_absent_at = now
    session.add(title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def unmark_title_absent_from_tmdb(session: Session, title: Title) -> Title:
    if title.tmdb_absent_at is None:
        message = "This title is not marked as one TMDB has no record of."
        raise HTTPException(status_code=409, detail=message)

    title.link_status = None
    title.tmdb_absent_at = None
    title.tmdb_title_validated_at = None
    session.add(title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def old_unlink_title_from_tmdb_title(
    session: Session,
    website_title: Title,
    tmdb_title: Title,
) -> Title:
    """Take `tmdb_title` off what `website_title` stands for.

    Episodes matched against it are unmatched, hand-made or not, and the rest
    are matched again against the links that are left.
    """
    _move_imported_channel_titles(session, website_title, [tmdb_title.id])
    for tmdb_title_link in list(website_title.tmdb_title_links):
        if tmdb_title_link.tmdb_title_id == tmdb_title.id:
            session.delete(tmdb_title_link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are matched against.
    session.expire(website_title, ["tmdb_title_links", "is_linked"])

    _lock_title_links(session, website_title)
    _old_unlink_episodes_from_dropped_tmdb_titles(session, website_title)
    _relink_episode(session, website_title)
    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def unlink_titles_from_tmdb_title(session: Session, tmdb_title: Title) -> None:
    for linked_title_link in list(tmdb_title.linked_title_links):
        old_unlink_title_from_tmdb_title(
            session,
            linked_title_link.linked_title,
            tmdb_title,
        )
    session.expire(tmdb_title, ["linked_title_links"])


# TODO: Validate
def old_make_title_unlinked(session: Session, website_title: Title) -> Title:
    """Make `website_title` canonical again, dropping every TMDB link it has."""
    if not website_title.tmdb_title_links:
        message = "This title is already a canonical title."
        raise HTTPException(status_code=409, detail=message)

    _move_imported_channel_titles(
        session,
        website_title,
        website_title.tmdb_title_ids,
    )
    _old_move_channel_titles_to_title(
        session,
        website_title,
        website_title.tmdb_title_ids,
    )

    for tmdb_title_link in list(website_title.tmdb_title_links):
        session.delete(tmdb_title_link)
    session.flush()
    session.expire(website_title, ["tmdb_title_links", "is_linked"])

    _lock_title_links(session, website_title)
    _old_unlink_episodes_from_dropped_tmdb_titles(session, website_title)
    session.commit()
    session.refresh(website_title)
    return website_title
