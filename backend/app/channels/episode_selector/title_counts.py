# TODO: Validate

from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from app.channels.episode_selector.watch_filters import started_title_ids
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.episodes import tmdb_record_id_of
from app.tmdb_media.filters import is_not_linked
from app.users.models import User


# TODO: Validate
def selected_title_ids(
    session: Session,
    user: User | None,
    episodes: list[Episode],
    channel_options: ChannelOptions,
) -> set[UUID] | None:
    total = channel_options.total_titles_count
    started_count = channel_options.started_titles_count
    new_count = channel_options.new_titles_count
    if total is None and started_count is None and new_count is None:
        return None
    if not user or not episodes:
        return None

    episode_to_titles = _titles_by_tmdb_episode(session, episodes)
    started: set[UUID] = set(session.exec(started_title_ids(user)).all())

    title_order: list[tuple[UUID, bool]] = []
    seen: set[UUID] = set()
    for episode in episodes:
        for title_id in episode_to_titles[tmdb_record_id_of(episode)]:
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
def _titles_by_tmdb_episode(
    session: Session,
    episodes: list[Episode],
) -> dict[UUID, set[UUID]]:
    tmdb_episode_ids = {tmdb_record_id_of(episode) for episode in episodes}
    counted_episode = aliased(Episode)
    counted_season = aliased(Season)
    counted_title = aliased(Title)
    counted_link = aliased(TitleTmdbTitle)
    tmdb_title_ids: dict[UUID, set[UUID]] = defaultdict(set)
    rows = session.exec(
        select(
            counted_episode.id,
            func.coalesce(
                col(counted_link.tmdb_title_id),
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
            is_not_linked(counted_episode),
            col(counted_episode.id).in_(tmdb_episode_ids),
        ),
    ).all()
    for tmdb_episode_id, tmdb_title_id in rows:
        tmdb_title_ids[tmdb_episode_id].add(tmdb_title_id)
    return tmdb_title_ids


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
