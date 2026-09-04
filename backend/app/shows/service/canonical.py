# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

import re
import uuid

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.service.creation import add_canonical_show
from app.channels.models import ChannelShow
from app.episodes.models import MANUAL_NOTE_PREFIX
from app.shows.models import Show
from app.shows.service.relinking import _relink_non_canonical_show
from app.utils import tz_datetime

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def add_canonical_show_and_link_episodes(
    session: Session,
    show: Show,
    canonical_show: Show | None = None,
) -> None:
    """Link `show` to the canonical show it is linked to, and read its episodes.

    A show TMDB has no match for is the canonical show, which is what it already is when
    it is written, so there is nothing to do for it here. One TMDB does have a match for
    is linked to that match, and `add_canonical_show` is what makes it non-canonical.

    A show already linked to a canonical show is left alone, since that may have
    been settled by hand and writing the show again is no reason to overrule it.
    A show linked to nothing is searched for afresh every time it is written,
    since a match that was not there to be found when it was first written can be
    there now.

    The episodes are read against the canonical show whether or not one was found
    here, because the episodes just written include ones the canonical show it is
    already linked to has never been read against.
    """
    if canonical_show:
        add_canonical_show(session, show, canonical_show)
    _relink_non_canonical_show(session, show)


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

    add_canonical_show(
        session,
        show,
        canonical_show,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)

    _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def set_canonical_show_using_tmdb_url(
    session: Session,
    show: Show,
    url: str,
) -> Show:
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
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import get_plugin_for_url  # noqa: PLC0415

    address = url.strip()
    if not canonical_show.is_canonical:
        message = "A show linked to a canonical show cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = get_plugin_for_url(address)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {address}")

    try:
        results = plugin_class(session).import_url(address, canonical_show)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    session.flush()
    session.expire(canonical_show, ["non_canonical_shows"])
    imported_keys = {result.show_key for result in results}
    for link in canonical_show.non_canonical_shows:
        if link.show.key not in imported_keys:
            continue
        link.show.canonical_show_validated_at = tz_datetime.now()
        link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        session.add(link.show)
        session.add(link)
        _relink_non_canonical_show(session, link.show)

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
    session.expire(show, ["canonical_show_links", "is_canonical"])

    _unlink_unlisted_episodes(session, show)
    _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def canonicalize_show(session: Session, show: Show) -> Show:
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
