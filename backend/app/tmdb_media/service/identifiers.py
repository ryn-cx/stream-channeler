# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

import uuid
from collections import defaultdict
from collections.abc import Collection

from sqlmodel import Session, col, select

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.titles.models import Title, TitleTmdbTitle
from app.tmdb_media.filters import is_linked, is_not_linked


# TODO: Validate
def tmdb_record_ids_by_key(
    session: Session,
    keys: Collection[str],
) -> dict[str, uuid.UUID]:
    """Map each episode key to the canonical episode that row stands for.

    An episode nothing else holds a record of is the record, so it stands for itself and
    answers with its own id. A non-canonical row answers with the episode it is linked
    to, and is preferred where both are stored, since the non-canonical row is the one
    the canonical row was minted for.

    Only episodes answer this way. A non-canonical title stands for however many
    canonical titles a website mixed into it and names none of them in a column, so a
    title key is asked of `tmdb_title_ids_by_key` and answered with all of them.
    """
    if not keys:
        return {}
    own_rows: dict[str, uuid.UUID] = dict(
        session.exec(
            select(Episode.key, Episode.id).where(
                col(Episode.key).in_(keys),
                is_not_linked(Episode),
            ),
        ).all(),
    )
    copy_rows: dict[str, uuid.UUID] = dict(
        session.exec(
            select(Episode.key, EpisodeTmdbEpisode.tmdb_episode_id)
            .select_from(Episode)
            .join(
                EpisodeTmdbEpisode,
                col(EpisodeTmdbEpisode.episode_id) == col(Episode.id),
            )
            .where(col(Episode.key).in_(keys)),
        ).all(),
    )
    return own_rows | copy_rows


# TODO: Validate
def tmdb_title_ids_by_key(
    session: Session,
    title_keys: Collection[str],
) -> dict[str, set[uuid.UUID]]:
    if not title_keys:
        return {}
    tmdb_title_ids: dict[str, set[uuid.UUID]] = defaultdict(set)
    copy_rows = session.exec(
        select(  # type: ignore[call-overload]
            Title.key,
            TitleTmdbTitle.tmdb_title_id,
        )
        .join(TitleTmdbTitle, col(TitleTmdbTitle.title_id) == col(Title.id))
        .where(is_linked(Title), col(Title.key).in_(title_keys)),
    ).all()
    for title_key, tmdb_title_id in copy_rows:
        tmdb_title_ids[title_key].add(tmdb_title_id)
    # A key naming a canonical title rather than a row standing for one is that
    # title, which is what TMDB's own records are: they are the canonical rows, so
    # importing one of them straight onto a channel has nothing to resolve
    # through anything else.
    title_rows = session.exec(
        select(  # type: ignore[call-overload]
            Title.key,
            Title.id,
        ).where(is_not_linked(Title), col(Title.key).in_(title_keys)),
    ).all()
    for title_key, tmdb_title_id in title_rows:
        tmdb_title_ids[title_key].add(tmdb_title_id)
    return tmdb_title_ids
