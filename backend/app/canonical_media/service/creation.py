# TODO: Validate
from sqlmodel import Session, col, select

from app.channels.models import ChannelTitle
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.titles.models import Title, TitleCanonicalTitle
from app.titles.service.relinking import _relink_non_canonical_title


# TODO: Validate
def _validate_titles(title: Title, tmdb_title: Title) -> None:
    """Validate that `title` and `tmdb_title` can be linked.

    The title cannot have any other canonical titles linked to it and it cannot be a TMDB
    title.

    The TMDB title must be canonical TMDB title."""
    if not tmdb_title.is_canonical:
        message = f"{tmdb_title} is not a canonical title."
        raise ValueError(message)
    if tmdb_title.source.plugin.key != TMDB_PLUGIN_KEY:
        message = f"{tmdb_title} is not a TMDB title."
        raise ValueError(message)
    if title.source.plugin.key == TMDB_PLUGIN_KEY:
        message = f"{title} is a TMDB title."
        raise ValueError(message)
    if title.non_canonical_title_links:
        message = f"{title} has other titles linked to it."
        raise ValueError(message)


# TODO: Validate
def link_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleCanonicalTitle:
    """Link a title to TMDB then links the title's episodes to TMDB.

    Will not remove any existing title links.
    Will relink existing titles to try to find better matches."""
    _validate_titles(title, tmdb_title)
    link: TitleCanonicalTitle
    if title.is_canonical:
        link = _link_canonical_title(session, title, tmdb_title, note)
    else:
        link = _link_non_canonical_title(title, tmdb_title, note)

    session.add(link)
    session.flush()
    session.expire(title, ["canonical_title_links", "is_canonical"])
    _relink_non_canonical_title(session, title)
    return link


# TODO: Validate
def _link_non_canonical_title(
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleCanonicalTitle:
    # If the link already exists nothing needs to be done.
    for tmdb_link in title.canonical_title_links:
        if tmdb_link.canonical_title_id == tmdb_title.id:
            return tmdb_link

    return TitleCanonicalTitle(
        title_id=title.id,
        canonical_title_id=tmdb_title.id,
        note=note,
    )


# TODO: Validate
def _link_canonical_title(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleCanonicalTitle:
    _update_channels(session, title, tmdb_title)

    return TitleCanonicalTitle(
        title_id=title.id,
        canonical_title_id=tmdb_title.id,
        note=note,
    )


# TODO: Validate
def _update_channels(
    session: Session,
    title: Title,
    canonical_title: Title,
) -> None:
    """Update channels to replace the original canonical title with the TMDB title."""
    channels_with_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.canonical_title_id == title.id,
            ),
        ).all(),
    )
    if not channels_with_title:
        return

    channels_with_title_and_tmdb_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.canonical_title_id == canonical_title.id,
                col(ChannelTitle.channel_id).in_(channels_with_title),
            ),
        ).all(),
    )
    for channel_id in channels_with_title - channels_with_title_and_tmdb_title:
        session.add(
            ChannelTitle(
                channel_id=channel_id,
                canonical_title_id=canonical_title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()
