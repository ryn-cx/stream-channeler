# TODO: Validate
"""Narrowing a channel's episodes down to a handful of its shows.

A channel that asks for a number of shows keeps every episode of the shows that
come first in the order already chosen and drops the rest, so the counts thin the
line-up without disturbing how it is sorted.
"""

from uuid import UUID

from sqlmodel import Session, col, select

from app.channels.episode_selector.watch_filters import started_show_ids
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.seasons.models import Season
from app.users.models import User


# TODO: Validate
def limit_shows(
    session: Session,
    user: User | None,
    episodes: list[Episode],
    channel_options: ChannelOptions,
) -> list[Episode]:
    """Keep only the episodes of the shows the counts leave room for.

    A show counts as started once the `User` has watched anything of it, which is
    what lets a channel ask for a few shows already under way alongside a few it
    has never touched. Without a `User` there is no such thing as started, so the
    counts do nothing.
    """
    total = channel_options.total_shows_count
    started_count = channel_options.started_shows_count
    new_count = channel_options.new_shows_count
    if total is None and started_count is None and new_count is None:
        return episodes
    if not user or not episodes:
        return episodes

    season_ids = {episode.season_id for episode in episodes}
    season_to_show: dict[UUID, UUID] = dict(
        session.exec(
            select(Season.id, Season.show_id).where(col(Season.id).in_(season_ids)),
        ).all(),
    )
    started: set[UUID] = set(session.exec(started_show_ids(user)).all())

    show_order: list[tuple[UUID, bool]] = []
    seen: set[UUID] = set()
    for episode in episodes:
        show_id = season_to_show[episode.season_id]
        if show_id in seen:
            continue
        seen.add(show_id)
        show_order.append((show_id, show_id in started))

    selected = _select_show_subset(
        show_order,
        total=total,
        started_count=started_count,
        new_count=new_count,
    )
    return [
        episode for episode in episodes if season_to_show[episode.season_id] in selected
    ]


# TODO: Validate
def _select_show_subset(
    show_order: list[tuple[UUID, bool]],
    total: int | None,
    started_count: int | None,
    new_count: int | None,
) -> set[UUID]:
    started_in_order = [show_id for show_id, is_started in show_order if is_started]
    new_in_order = [show_id for show_id, is_started in show_order if not is_started]

    if total is not None and started_count is None and new_count is None:
        return {show_id for show_id, _ in show_order[:total]}

    selected_started: list[UUID] | None = (
        started_in_order[:started_count] if started_count is not None else None
    )
    selected_new: list[UUID] | None = (
        new_in_order[:new_count] if new_count is not None else None
    )

    if selected_started is None:
        if total is None:
            selected_started = started_in_order
        else:
            remaining = max(0, total - len(selected_new or []))
            selected_started = started_in_order[:remaining]
    if selected_new is None:
        if total is None:
            selected_new = new_in_order
        else:
            remaining = max(0, total - len(selected_started))
            selected_new = new_in_order[:remaining]

    selected = set(selected_started) | set(selected_new)

    if total is not None and len(selected) > total:
        trimmed: set[UUID] = set()
        for show_id, _ in show_order:
            if show_id in selected:
                trimmed.add(show_id)
                if len(trimmed) >= total:
                    break
        selected = trimmed

    return selected
