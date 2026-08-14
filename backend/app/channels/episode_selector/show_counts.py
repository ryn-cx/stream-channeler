# TODO: Validate
"""Narrowing a channel's episodes down to a handful of its shows.

A channel that asks for a number of shows keeps every episode of the shows that
come first in the order already chosen and drops the rest, so the counts thin the
line-up without disturbing how it is sorted.

A show here is the canonical show rather than one website's row for it, so a
show two websites carry counts once, and a row that mixes shows counts as each of
the canonical shows its episodes belong to.
"""

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from app.canonical_media.filters import (
    canonical_id_of,
    is_canonical,
)
from app.channels.episode_selector.watch_filters import started_show_ids
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
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

    episode_to_shows = _titles_by_canonical_episode(session, episodes)
    started: set[UUID] = set(session.exec(started_show_ids(user)).all())

    show_order: list[tuple[UUID, bool]] = []
    seen: set[UUID] = set()
    for episode in episodes:
        for show_id in episode_to_shows[canonical_id_of(episode)]:
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
    # An episode of a row that mixes shows belongs to each of them alike, so room
    # left for any one of its canonical shows is room for the episode.
    return [
        episode
        for episode in episodes
        if not selected.isdisjoint(episode_to_shows[canonical_id_of(episode)])
    ]


# TODO: Validate
def _titles_by_canonical_episode(
    session: Session,
    episodes: list[Episode],
) -> dict[UUID, set[UUID]]:
    """Map each episode in `episodes` to the canonical shows it belongs to.

    Read off the episode's own canonical row rather than off the row holding it,
    since a row that mixes shows holds episodes of each of them. An episode
    nothing was minted for it to stand for sits under a website's own row, so
    there the canonical shows are the ones that row stands for - all of them,
    since a row stands for one no more than for another.
    """
    canonical_episode_ids = {canonical_id_of(episode) for episode in episodes}
    counted_episode = aliased(Episode)
    counted_season = aliased(Season)
    counted_show = aliased(Show)
    counted_link = aliased(ShowCanonicalShow)
    canonical_show_ids: dict[UUID, set[UUID]] = defaultdict(set)
    rows = session.exec(
        select(
            counted_episode.id,
            func.coalesce(
                col(counted_link.canonical_show_id),
                col(counted_show.id),
            ),
        )
        .select_from(counted_episode)
        .join(
            counted_season,
            col(counted_episode.season_id) == col(counted_season.id),
        )
        .join(counted_show, col(counted_season.show_id) == col(counted_show.id))
        # A canonical row has no links and stands for itself; a non-canonical one
        # has a link per canonical show and stands for each.
        .outerjoin(counted_link, col(counted_link.show_id) == col(counted_show.id))
        .where(
            is_canonical(counted_episode),
            col(counted_episode.id).in_(canonical_episode_ids),
        ),
    ).all()
    for canonical_episode_id, canonical_show_id in rows:
        canonical_show_ids[canonical_episode_id].add(canonical_show_id)
    return canonical_show_ids


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
