# TODO: Validate
"""Narrowing a channel's episodes down to a handful of its titles.

A channel that asks for a number of titles keeps every episode of the titles that
come first in the order already chosen and drops the rest, so the counts thin the
line-up without disturbing how it is sorted.

A title here is the canonical title rather than one website's row for it, so a
title two websites carry counts once, and a row that mixes titles counts as each of
the canonical titles its episodes belong to.
"""

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from app.canonical_media.episodes import canonical_id_of
from app.canonical_media.filters import is_canonical
from app.channels.episode_selector.watch_filters import started_title_ids
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title, TitleCanonicalTitle
from app.users.models import User


# TODO: Validate
def selected_title_ids(
    session: Session,
    user: User | None,
    episodes: list[Episode],
    channel_options: ChannelOptions,
) -> set[UUID] | None:
    """Return the titles the counts leave room for, or None where they leave every one.

    A title counts as started once the `User` has watched anything of it, which is
    what lets a channel ask for a few titles already under way alongside a few it
    has never touched. Without a `User` there is no such thing as started, so the
    counts do nothing.
    """
    total = channel_options.total_titles_count
    started_count = channel_options.started_titles_count
    new_count = channel_options.new_titles_count
    if total is None and started_count is None and new_count is None:
        return None
    if not user or not episodes:
        return None

    episode_to_titles = _titles_by_canonical_episode(session, episodes)
    started: set[UUID] = set(session.exec(started_title_ids(user)).all())

    title_order: list[tuple[UUID, bool]] = []
    seen: set[UUID] = set()
    for episode in episodes:
        for title_id in episode_to_titles[canonical_id_of(episode)]:
            if title_id in seen:
                continue
            seen.add(title_id)
            title_order.append((title_id, title_id in started))

    return _select_title_subset(
        title_order,
        total=total,
        started_count=started_count,
        new_count=new_count,
    )


# TODO: Validate
def _titles_by_canonical_episode(
    session: Session,
    episodes: list[Episode],
) -> dict[UUID, set[UUID]]:
    """Map each episode in `episodes` to the canonical titles it belongs to.

    Read off the episode's own canonical row rather than off the row holding it,
    since a row that mixes titles holds episodes of each of them. An episode
    nothing was minted for it to stand for sits under a website's own row, so
    there the canonical titles are the ones that row stands for - all of them,
    since a row stands for one no more than for another.
    """
    canonical_episode_ids = {canonical_id_of(episode) for episode in episodes}
    counted_episode = aliased(Episode)
    counted_season = aliased(Season)
    counted_title = aliased(Title)
    counted_link = aliased(TitleCanonicalTitle)
    canonical_title_ids: dict[UUID, set[UUID]] = defaultdict(set)
    rows = session.exec(
        select(
            counted_episode.id,
            func.coalesce(
                col(counted_link.canonical_title_id),
                col(counted_title.id),
            ),
        )
        .select_from(counted_episode)
        .join(
            counted_season,
            col(counted_episode.season_id) == col(counted_season.id),
        )
        .join(counted_title, col(counted_season.title_id) == col(counted_title.id))
        # A canonical row has no links and stands for itself; a non-canonical one
        # has a link per canonical title and stands for each.
        .outerjoin(counted_link, col(counted_link.title_id) == col(counted_title.id))
        .where(
            is_canonical(counted_episode),
            col(counted_episode.id).in_(canonical_episode_ids),
        ),
    ).all()
    for canonical_episode_id, canonical_title_id in rows:
        canonical_title_ids[canonical_episode_id].add(canonical_title_id)
    return canonical_title_ids


# TODO: Validate
def _select_title_subset(
    title_order: list[tuple[UUID, bool]],
    total: int | None,
    started_count: int | None,
    new_count: int | None,
) -> set[UUID]:
    started_in_order = [title_id for title_id, is_started in title_order if is_started]
    new_in_order = [title_id for title_id, is_started in title_order if not is_started]

    if total is not None and started_count is None and new_count is None:
        return {title_id for title_id, _ in title_order[:total]}

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
        for title_id, _ in title_order:
            if title_id in selected:
                trimmed.add(title_id)
                if len(trimmed) >= total:
                    break
        selected = trimmed

    return selected
