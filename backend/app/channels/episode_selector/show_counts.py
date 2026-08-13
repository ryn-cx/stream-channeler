# TODO: Validate
"""Narrowing a channel's episodes down to a handful of its shows.

A channel that asks for a number of shows keeps every episode of the shows that
come first in the order already chosen and drops the rest, so the counts thin the
line-up without disturbing how it is sorted.

A show here is the title rather than one website's listing of it, so a title two
websites carry counts once, and a listing that mixes titles counts as each of the
titles its episodes belong to.
"""

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
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

    episode_to_show = _titles_by_canonical_episode(session, episodes)
    started: set[UUID] = set(session.exec(started_show_ids(user)).all())

    show_order: list[tuple[UUID, bool]] = []
    seen: set[UUID] = set()
    for episode in episodes:
        show_id = episode_to_show[episode.canonical_episode_id]
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
        episode
        for episode in episodes
        if episode_to_show[episode.canonical_episode_id] in selected
    ]


# TODO: Validate
def _titles_by_canonical_episode(
    session: Session,
    episodes: list[Episode],
) -> dict[UUID, UUID]:
    """Map each episode in `episodes` to the title it belongs to.

    Read off the episode's own canonical row rather than off the listing holding
    it, since a listing that mixes titles holds episodes of each of them.
    """
    canonical_episode_ids = {episode.canonical_episode_id for episode in episodes}
    counted_episode = aliased(Episode)
    counted_season = aliased(Season)
    return dict(
        session.exec(
            select(counted_episode.id, counted_season.show_id)
            .join(
                counted_season,
                col(counted_episode.season_id) == col(counted_season.id),
            )
            .where(
                is_canonical(counted_episode),
                is_canonical(counted_season),
                col(counted_episode.id).in_(canonical_episode_ids),
            ),
        ).all(),
    )


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
