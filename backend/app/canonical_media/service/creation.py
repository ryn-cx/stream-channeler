# TODO: Validate
from sqlmodel import Session, col, select

from app.channels.models import ChannelShow
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.shows.models import Show, ShowCanonicalShow
from app.shows.service.relinking import _relink_non_canonical_show


def _validate_shows(show: Show, tmdb_show: Show) -> None:
    """Validate that `show` and `tmdb_show` can be linked.

    The show cannot have any other canonical shows linked to it and it cannot be a TMDB
    show.

    The TMDB show must be canonical TMDB show."""
    if not tmdb_show.is_canonical:
        message = f"{tmdb_show} is not a canonical show."
        raise ValueError(message)
    if tmdb_show.source.plugin.key != TMDB_PLUGIN_KEY:
        message = f"{tmdb_show} is not a TMDB show."
        raise ValueError(message)
    if show.source.plugin.key == TMDB_PLUGIN_KEY:
        message = f"{show} is a TMDB show."
        raise ValueError(message)
    if show.non_canonical_shows:
        message = f"{show} has other shows linked to it."
        raise ValueError(message)


# TODO: Validate
def link_show_to_tmdb(
    session: Session,
    show: Show,
    tmdb_show: Show,
    note: str,
) -> ShowCanonicalShow:
    """Link a show to TMDB then links the show's episodes to TMDB.

    Will not remove any existing show links.
    Will relink existing shows to try to find better matches."""
    _validate_shows(show, tmdb_show)
    link: ShowCanonicalShow
    if show.is_canonical:
        link = _link_canonical_show(session, show, tmdb_show, note)
    else:
        link = _link_non_canonical_show(show, tmdb_show, note)

    session.add(link)
    session.flush()
    session.expire(show, ["canonical_show_links", "is_canonical"])
    _relink_non_canonical_show(session, show)
    return link


def _link_non_canonical_show(
    show: Show,
    tmdb_show: Show,
    note: str,
) -> ShowCanonicalShow:
    # If the link already exists nothing needs to be done.
    for tmdb_link in show.canonical_show_links:
        if tmdb_link.canonical_show_id == tmdb_show.id:
            return tmdb_link

    return ShowCanonicalShow(
        show_id=show.id,
        canonical_show_id=tmdb_show.id,
        note=note,
    )


# TODO: Validate
def _link_canonical_show(
    session: Session,
    show: Show,
    tmdb_show: Show,
    note: str,
) -> ShowCanonicalShow:
    _update_channels(session, show, tmdb_show)

    return ShowCanonicalShow(
        show_id=show.id,
        canonical_show_id=tmdb_show.id,
        note=note,
    )


# TODO: Validate
def _update_channels(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> None:
    """Update channels to replace the original canonical show with the TMDB show."""
    channels_with_show = set(
        session.exec(
            select(ChannelShow.channel_id).where(
                ChannelShow.canonical_show_id == show.id,
            ),
        ).all(),
    )
    if not channels_with_show:
        return

    channels_with_show_and_tmdb_show = set(
        session.exec(
            select(ChannelShow.channel_id).where(
                ChannelShow.canonical_show_id == canonical_show.id,
                col(ChannelShow.channel_id).in_(channels_with_show),
            ),
        ).all(),
    )
    for channel_id in channels_with_show - channels_with_show_and_tmdb_show:
        session.add(
            ChannelShow(
                channel_id=channel_id,
                canonical_show_id=canonical_show.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()
