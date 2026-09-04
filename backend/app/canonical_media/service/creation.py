# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

from sqlmodel import Session, col, select

from app.channels.models import ChannelShow
from app.shows.models import Show, ShowCanonicalShow


# TODO: Validate
def add_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
    note: str = "Automatic: Import match",
) -> ShowCanonicalShow:
    """Record that `show` stands for the canonical show `canonical_show`.

    A non-canonical row stands for every canonical show linked to it and no more for one
    than for another, so this adds one to the set and settles nothing about which of
    them the row is chiefly about. Nothing else is settled either: what a listing stands
    for as a whole, and the reading of its episodes against it, is `settle_show`.
    """
    # If this show is not canonical
    if not canonical_show.is_canonical:
        message = f"{canonical_show} is not a canonical show."
        raise ValueError(message)
    if show.non_canonical_shows:
        message = f"{show} has other shows linked to it."
        raise ValueError(message)

    if show.is_canonical:
        _follow_show_to_canonical_show(session, show, canonical_show)

    existing_canonical_show = None
    for candidate in show.canonical_show_links:
        # By the row where the link is already stored, and by the object itself
        # where it is not: a link made this session names the canonical show it
        # holds rather than its id, which the flush is what writes.
        if (
            candidate.canonical_show is canonical_show
            or candidate.canonical_show_id == canonical_show.id
        ):
            existing_canonical_show = candidate
            break

    if existing_canonical_show is None:
        existing_canonical_show = ShowCanonicalShow(
            show=show,
            canonical_show=canonical_show,
            note=note,
        )
        session.add(existing_canonical_show)

    session.flush()
    session.expire(show, ["is_canonical"])
    return existing_canonical_show


# TODO: Validate
def _follow_show_to_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> None:
    holding_channel_ids = set(
        session.exec(
            select(ChannelShow.channel_id).where(
                ChannelShow.canonical_show_id == show.id,
            ),
        ).all(),
    )
    if not holding_channel_ids:
        return

    already_holding = set(
        session.exec(
            select(ChannelShow.channel_id).where(
                ChannelShow.canonical_show_id == canonical_show.id,
                col(ChannelShow.channel_id).in_(holding_channel_ids),
            ),
        ).all(),
    )
    for channel_id in holding_channel_ids - already_holding:
        session.add(
            ChannelShow(
                channel_id=channel_id,
                canonical_show_id=canonical_show.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()
