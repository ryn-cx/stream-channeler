# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

import uuid
from collections import defaultdict
from collections.abc import Collection

from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical, is_non_canonical
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.shows.models import Show, ShowCanonicalShow


# TODO: Validate
def canonical_ids_by_key(
    session: Session,
    keys: Collection[str],
) -> dict[str, uuid.UUID]:
    """Map each episode key to the canonical episode that row stands for.

    An episode nothing else holds a record of is the record, so it stands for itself and
    answers with its own id. A non-canonical row answers with the episode it is linked
    to, and is preferred where both are stored, since the non-canonical row is the one
    the canonical row was minted for.

    Only episodes answer this way. A non-canonical show stands for however many
    canonical shows a website mixed into it and names none of them in a column, so a
    show key is asked of `canonical_show_ids_by_key` and answered with all of them.
    """
    if not keys:
        return {}
    own_rows: dict[str, uuid.UUID] = dict(
        session.exec(
            select(Episode.key, Episode.id).where(
                col(Episode.key).in_(keys),
                is_canonical(Episode),
            ),
        ).all(),
    )
    copy_rows: dict[str, uuid.UUID] = dict(
        session.exec(
            select(Episode.key, EpisodeCanonicalEpisode.canonical_episode_id)
            .select_from(Episode)
            .join(
                EpisodeCanonicalEpisode,
                col(EpisodeCanonicalEpisode.episode_id) == col(Episode.id),
            )
            .where(col(Episode.key).in_(keys)),
        ).all(),
    )
    return own_rows | copy_rows


# TODO: Validate
def canonical_show_ids_by_key(
    session: Session,
    show_keys: Collection[str],
) -> dict[str, set[uuid.UUID]]:
    if not show_keys:
        return {}
    canonical_show_ids: dict[str, set[uuid.UUID]] = defaultdict(set)
    copy_rows = session.exec(
        select(  # type: ignore[call-overload]
            Show.key,
            ShowCanonicalShow.canonical_show_id,
        )
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Show.id))
        .where(is_non_canonical(Show), col(Show.key).in_(show_keys)),
    ).all()
    for show_key, canonical_show_id in copy_rows:
        canonical_show_ids[show_key].add(canonical_show_id)
    # A key naming a canonical show rather than a row standing for one is that
    # show, which is what TMDB's own records are: they are the canonical rows, so
    # importing one of them straight onto a channel has nothing to resolve
    # through anything else.
    title_rows = session.exec(
        select(  # type: ignore[call-overload]
            Show.key,
            Show.id,
        ).where(is_canonical(Show), col(Show.key).in_(show_keys)),
    ).all()
    for show_key, canonical_show_id in title_rows:
        canonical_show_ids[show_key].add(canonical_show_id)
    return canonical_show_ids
