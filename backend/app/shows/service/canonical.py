# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

import re
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.service.creation import link_show_to_tmdb
from app.channels.models import ChannelShow
from app.episodes.models import MANUAL_NOTE_PREFIX
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.shows.models import Show
from app.shows.service.relinking import _relink_non_canonical_show
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import MediaNotFoundError

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import AbstractPlugin

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def match_show_to_tmdb(
    session: Session,
    show: Show,
    tmdb_show: Show | None = None,
    note: str = "Automatic: Import match",
) -> None:
    """Link `show` to `tmdb_show` when one was found, then match its episodes.

    The episodes are matched either way, since an import writes episodes that the
    already-linked TMDB show has never been matched against.
    """
    if show.source.plugin.key == TMDB_PLUGIN_KEY:
        return
    if tmdb_show:
        link_show_to_tmdb(session, show, tmdb_show, note)
    else:
        _relink_non_canonical_show(session, show)


# TODO: Validate
def match_imported_shows_to_tmdb(
    session: Session,
    plugin_instance: AbstractPlugin,
    shows: Sequence[Show],
) -> None:
    """Search TMDB for every show `plugin_instance` imported and link what is found.

    A show already linked to a title is left as it is, since the link it carries
    may have been settled by hand.
    """
    for show in shows:
        if not show.is_canonical:
            continue
        tmdb_show = _find_tmdb_show(session, plugin_instance, show)
        match_show_to_tmdb(session, show, tmdb_show)


# TODO: Validate
def _find_tmdb_show(
    session: Session,
    plugin_instance: AbstractPlugin,
    show: Show,
) -> Show | None:
    """Return the TMDB show `show` is a listing of, importing it where it is new."""
    from plugins.TMDB import TMDB  # noqa: PLC0415

    if not plugin_instance.implements("tmdb_lookup_info"):
        return None

    title, media_type, year = plugin_instance.tmdb_lookup_info(show.key)
    tmdb_plugin = TMDB(session)
    try:
        results = tmdb_plugin.import_search([title], media_type, year)
    except MediaNotFoundError:
        return None
    return next(iter(tmdb_plugin.imported_shows(results)), None)


# TODO: Validate
def set_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> Show:
    """Add an admin's chosen `canonical_show` to what `show` stands for.

    Added alongside any existing links rather than replacing them, since one page
    can hold several shows. Removing one is `unset_canonical_show`. The choice is
    locked so the next import cannot overrule it.
    """
    if show.non_canonical_show_links:
        message = "A show other shows are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )

    link_show_to_tmdb(
        session,
        show,
        canonical_show,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    remove_plugin_unmatched_sources(session, canonical_show.id, show.source.plugin.key)
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)

    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def set_canonical_show_using_tmdb_url(
    session: Session,
    show: Show,
    url: str,
) -> Show:
    """Import the TMDB title at `url` and link `show` to it."""
    from plugins.TMDB import TMDB  # noqa: PLC0415

    address = url.strip()
    if not _TMDB_TITLE_URL.search(address):
        raise HTTPException(
            status_code=400,
            detail=f"{url} is not the address of a TMDB film or series",
        )

    imported = TMDB(session).import_url(address)
    canonical_show = session.exec(
        select(Show).where(is_canonical(Show), Show.key == imported[0].show_key),
    ).one()
    return set_canonical_show(session, show, canonical_show)


# TODO: Validate
def import_non_canonical_show_from_url(
    session: Session,
    canonical_show: Show,
    url: str,
) -> Show:
    """Import the show at `url` and link it to `canonical_show`."""
    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import get_plugin_for_url  # noqa: PLC0415

    address = url.strip()
    if not canonical_show.is_canonical:
        message = "A show linked to a canonical show cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = get_plugin_for_url(address)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {address}")

    plugin_instance = plugin_class(session)
    try:
        results = plugin_instance.import_url(address)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for imported_show in plugin_instance.imported_shows(results):
        match_show_to_tmdb(session, imported_show, canonical_show)

    remove_plugin_unmatched_sources(
        session,
        canonical_show.id,
        plugin_class.plugin_name(),
    )
    session.flush()
    session.expire(canonical_show, ["non_canonical_show_links"])
    imported_keys = {result.show_key for result in results}
    for link in canonical_show.non_canonical_show_links:
        if link.non_canonical_show.key not in imported_keys:
            continue
        link.non_canonical_show.canonical_show_validated_at = tz_datetime.now()
        link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        session.add(link.non_canonical_show)
        session.add(link)

    session.commit()
    session.refresh(canonical_show)
    return canonical_show


# TODO: Validate
def unset_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> Show:
    """Take `canonical_show` off what `show` stands for.

    Episodes matched against it are unmatched, hand-settled or not, and the rest
    are matched again against the links that are left. The lock is left as it is.
    """
    for link in list(show.canonical_show_links):
        if link.canonical_show_id == canonical_show.id:
            session.delete(link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are settled against.
    session.expire(show, ["canonical_show_links", "is_canonical"])

    _unlink_unlisted_episodes(session, show)
    _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def canonicalize_show(session: Session, show: Show) -> Show:
    """Make `show` canonical again, dropping every TMDB link it has."""
    if not show.canonical_show_links:
        message = "This show is already a canonical show."
        raise HTTPException(status_code=409, detail=message)

    _add_channel_shows(session, show, show.canonical_show_ids)

    for link in list(show.canonical_show_links):
        session.delete(link)
    session.flush()
    session.expire(show, ["canonical_show_links", "is_canonical"])

    _unlink_unlisted_episodes(session, show)
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def _add_channel_shows(
    session: Session,
    show: Show,
    previous_canonical_show_ids: list[uuid.UUID],
) -> None:
    """Move channel membership from the previous canonical shows onto `show`."""
    channel_ids = set(
        session.exec(
            select(ChannelShow.channel_id).where(
                ChannelShow.canonical_show_id == show.id,
            ),
        ).all(),
    )
    previous_channel_shows = session.exec(
        select(ChannelShow).where(
            col(ChannelShow.canonical_show_id).in_(previous_canonical_show_ids),
        ),
    ).all()
    for channel_show in previous_channel_shows:
        if channel_show.channel_id in channel_ids:
            continue
        channel_ids.add(channel_show.channel_id)
        session.add(
            ChannelShow(
                channel_id=channel_show.channel_id,
                canonical_show_id=show.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


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
            session.expire(episode, ["canonical_episode_links", "is_canonical"])

            if not episode.canonical_episode_links:
                episode.canonical_episode_validated_at = None
                episode.canonical_episode_note = None
                session.add(episode)
    session.flush()
