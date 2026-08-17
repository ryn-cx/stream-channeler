# TODO: Validate
"""The season an episode belongs to.

An episode that stands for a canonical episode belongs to the season that
canonical episode is under; one that stands for nothing belongs to the season its
own website filed it under.
"""

import uuid
from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, func, select

from app.canonical_media.episodes import canonical_episode_link, links_of
from app.episodes.models import Episode
from app.seasons.models import Season


# TODO: Validate
def season_id_column(
    episode: Any,  # noqa: ANN401 - A model class or an alias of one.
    canonical_episode: Any,  # noqa: ANN401 - A model class or an alias of one.
) -> ColumnElement[uuid.UUID]:
    """Return the season `episode` belongs to, as SQL reads it."""
    return func.coalesce(
        col(canonical_episode.season_id),
        col(episode.season_id),
    )


# TODO: Validate
def season_ids_by_episode(
    session: Session,
    episodes: Sequence[Episode],
) -> dict[uuid.UUID, uuid.UUID]:
    """Return the season each of `episodes` belongs to, keyed by the episode.

    A row standing for more than one episode belongs to no one of their seasons
    more than another, so it is left under the season its own website filed it
    under rather than handed whichever season came first.
    """
    canonical_ids = {
        canonical_id
        for episode in episodes
        if (canonical_id := episode.sole_canonical_episode_id) is not None
    }
    canonical_seasons = _season_ids(session, canonical_ids)
    return {
        episode.id: canonical_seasons.get(
            episode.sole_canonical_episode_id,
            episode.season_id,
        )
        for episode in episodes
    }


# TODO: Validate
def _season_ids(
    session: Session,
    episode_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, uuid.UUID]:
    if not episode_ids:
        return {}
    rows = session.exec(
        select(Episode.id, Episode.season_id).where(  # type: ignore[call-overload]
            col(Episode.id).in_(episode_ids),
        ),
    ).all()
    return dict(rows)


# TODO: Validate
def season_ids_by_key(
    session: Session,
    season_keys: Collection[str],
) -> dict[str, uuid.UUID]:
    """Return the season each of `season_keys` names a filter for."""
    if not season_keys:
        return {}
    canonical_episode = aliased(Episode)
    canonical_link = canonical_episode_link()
    rows = session.exec(
        select(  # type: ignore[call-overload]
            Season.key,
            Season.id,
            season_id_column(Episode, canonical_episode),
        )
        .select_from(Season)
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .outerjoin(canonical_link, links_of(Episode, canonical_link))
        .outerjoin(
            canonical_episode,
            col(canonical_link.canonical_episode_id) == col(canonical_episode.id),
        )
        .where(col(Season.key).in_(season_keys)),
    ).all()
    season_ids: dict[str, uuid.UUID] = {}
    for key, own_id, season_id in rows:
        if key not in season_ids or season_ids[key] == own_id:
            season_ids[key] = season_id
    return season_ids
