# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

import re
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.service.creation import link_title_to_tmdb
from app.channels.models import ChannelTitle
from app.episodes.models import MANUAL_NOTE_PREFIX
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.titles.models import Title
from app.titles.service.relinking import _relink_non_canonical_title
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import MediaNotFoundError

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import AbstractPlugin, TMDBLookupInfo

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def match_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title | None = None,
    note: str = "Automatic: Import match",
) -> None:
    """Link `title` to `tmdb_title` when one was found, then match its episodes.

    The episodes are matched either way, since an import writes episodes that the
    already-linked TMDB title has never been matched against.
    """
    if title.source.plugin.key == TMDB_PLUGIN_KEY:
        return
    if tmdb_title:
        link_title_to_tmdb(session, title, tmdb_title, note)
    else:
        _relink_non_canonical_title(session, title)


# TODO: Validate
def match_imported_titles_to_tmdb(
    session: Session,
    plugin_instance: AbstractPlugin,
    titles: Sequence[Title],
) -> None:
    """Search TMDB for every title `plugin_instance` imported and link what is found.

    A title already linked to a title is left as it is, since the link it carries
    may have been settled by hand.
    """
    for title in titles:
        if not title.is_canonical:
            continue
        link_title_to_tmdb_lookups(
            session,
            title,
            plugin_instance.tmdb_lookup_info(title.key),
        )


# TODO: Validate
def link_title_to_tmdb_lookups(
    session: Session,
    title: Title,
    lookup_infos: Sequence[TMDBLookupInfo],
) -> None:
    if not title.is_canonical:
        return
    match_title_to_tmdb(session, title, _find_tmdb_title(session, lookup_infos))


# TODO: Validate
def _find_tmdb_title(
    session: Session,
    lookup_infos: Sequence[TMDBLookupInfo],
) -> Title | None:
    from plugins.TMDB import TMDB  # noqa: PLC0415

    tmdb_plugin = TMDB(session)
    for lookup_info in lookup_infos:
        try:
            results = tmdb_plugin.import_search(
                [lookup_info.name],
                lookup_info.media_type,
                lookup_info.year,
            )
        except MediaNotFoundError:
            continue
        if tmdb_title := next((result.title for result in results), None):
            return tmdb_title
    return None


# TODO: Validate
def set_canonical_title(
    session: Session,
    title: Title,
    canonical_title: Title,
) -> Title:
    """Add an admin's chosen `canonical_title` to what `title` stands for.

    Added alongside any existing links rather than replacing them, since one page
    can hold several titles. Removing one is `unset_canonical_title`. The choice is
    locked so the next import cannot overrule it.
    """
    if title.non_canonical_title_links:
        message = "A title other titles are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )

    link_title_to_tmdb(
        session,
        title,
        canonical_title,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    remove_plugin_unmatched_sources(
        session,
        canonical_title.id,
        title.source.plugin.key,
    )
    title.canonical_title_validated_at = tz_datetime.now()
    session.add(title)

    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def set_canonical_title_using_tmdb_url(
    session: Session,
    title: Title,
    url: str,
) -> Title:
    """Import the TMDB title at `url` and link `title` to it."""
    from plugins.TMDB import TMDB  # noqa: PLC0415

    address = url.strip()
    if not _TMDB_TITLE_URL.search(address):
        raise HTTPException(
            status_code=400,
            detail=f"{url} is not the address of a TMDB film or series",
        )

    imported = TMDB(session).import_url(address)
    canonical_title = session.exec(
        select(Title).where(is_canonical(Title), Title.key == imported[0].title.key),
    ).one()
    return set_canonical_title(session, title, canonical_title)


# TODO: Validate
def import_non_canonical_title_from_url(
    session: Session,
    canonical_title: Title,
    url: str,
) -> Title:
    """Import the title at `url` and link it to `canonical_title`."""
    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import get_plugin_for_url  # noqa: PLC0415

    address = url.strip()
    if not canonical_title.is_canonical:
        message = "A title linked to a canonical title cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = get_plugin_for_url(address)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {address}")

    plugin_instance = plugin_class(session)
    try:
        results = plugin_instance.import_url(address)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for result in results:
        match_title_to_tmdb(session, result.title, canonical_title)

    remove_plugin_unmatched_sources(
        session,
        canonical_title.id,
        plugin_class.plugin_name(),
    )
    session.flush()
    session.expire(canonical_title, ["non_canonical_title_links"])
    imported_keys = {result.title.key for result in results}
    for link in canonical_title.non_canonical_title_links:
        if link.non_canonical_title.key not in imported_keys:
            continue
        link.non_canonical_title.canonical_title_validated_at = tz_datetime.now()
        link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        session.add(link.non_canonical_title)
        session.add(link)

    session.commit()
    session.refresh(canonical_title)
    return canonical_title


# TODO: Validate
def unset_canonical_title(
    session: Session,
    title: Title,
    canonical_title: Title,
) -> Title:
    """Take `canonical_title` off what `title` stands for.

    Episodes matched against it are unmatched, hand-settled or not, and the rest
    are matched again against the links that are left. The lock is left as it is.
    """
    for link in list(title.canonical_title_links):
        if link.canonical_title_id == canonical_title.id:
            session.delete(link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are settled against.
    session.expire(title, ["canonical_title_links", "is_canonical"])

    _unlink_unlisted_episodes(session, title)
    _relink_non_canonical_title(session, title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def canonicalize_title(session: Session, title: Title) -> Title:
    """Make `title` canonical again, dropping every TMDB link it has."""
    if not title.canonical_title_links:
        message = "This title is already a canonical title."
        raise HTTPException(status_code=409, detail=message)

    _add_channel_titles(session, title, title.canonical_title_ids)

    for link in list(title.canonical_title_links):
        session.delete(link)
    session.flush()
    session.expire(title, ["canonical_title_links", "is_canonical"])

    _unlink_unlisted_episodes(session, title)
    title.canonical_title_validated_at = tz_datetime.now()
    session.add(title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def _add_channel_titles(
    session: Session,
    title: Title,
    previous_canonical_title_ids: list[uuid.UUID],
) -> None:
    """Move channel membership from the previous canonical titles onto `title`."""
    channel_ids = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.canonical_title_id == title.id,
            ),
        ).all(),
    )
    previous_channel_titles = session.exec(
        select(ChannelTitle).where(
            col(ChannelTitle.canonical_title_id).in_(previous_canonical_title_ids),
        ),
    ).all()
    for channel_title in previous_channel_titles:
        if channel_title.channel_id in channel_ids:
            continue
        channel_ids.add(channel_title.channel_id)
        session.add(
            ChannelTitle(
                channel_id=channel_title.channel_id,
                canonical_title_id=title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


# TODO: Validate
def _unlink_unlisted_episodes(session: Session, title: Title) -> None:
    """Take every episode of `title` off a record no linked title holds."""
    canonical_title_ids = {linked.id for linked in title.canonical_titles}
    for season in title.active_children:
        for episode in season.active_children:
            for link in list(episode.canonical_episode_links):
                if link.canonical_episode.season.title_id in canonical_title_ids:
                    continue
                session.delete(link)
            session.flush()
            session.expire(episode, ["canonical_episode_links", "is_canonical"])

            if not episode.canonical_episode_links:
                episode.canonical_episode_validated_at = None
                session.add(episode)
    session.flush()
