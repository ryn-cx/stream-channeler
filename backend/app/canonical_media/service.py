# TODO: Validate
"""The canonical rows TMDB writes, and which titles a listing is a copy of."""

import uuid
from collections import defaultdict
from collections.abc import Collection

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical, is_copy
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow


# TODO: Validate
def _cache[CanonicalT: Show | Season | Episode](
    session: Session,
    model: type[CanonicalT],
) -> dict[tuple[str, ...], CanonicalT]:
    cache: dict[tuple[str, ...], CanonicalT] = session.info.setdefault(
        model.__name__,
        {},
    )
    return cache


# TODO: Validate
def _loaded_parents(session: Session) -> set[uuid.UUID]:
    loaded: set[uuid.UUID] = session.info.setdefault("canonical_loaded_parents", set())
    return loaded


# TODO: Validate
def _remembered[CanonicalT: Show | Season | Episode](
    session: Session,
    model: type[CanonicalT],
    cache_key: tuple[str, ...],
) -> CanonicalT | None:
    remembered = _cache(session, model).get(cache_key)
    if remembered is None or remembered not in session:
        return None
    return remembered


# TODO: Validate
def _remember(
    session: Session,
    canonical: Show | Season | Episode,
    cache_key: tuple[str, ...],
) -> None:
    _cache(session, type(canonical))[cache_key] = canonical


# TODO: Validate
def _remember_title(session: Session, canonical_show: Show) -> None:
    _remember(session, canonical_show, (canonical_show.key,))
    loaded = _loaded_parents(session)
    loaded.add(canonical_show.id)
    for canonical_season in canonical_show.seasons:
        _remember(
            session,
            canonical_season,
            (str(canonical_show.id), canonical_season.key),
        )
        loaded.add(canonical_season.id)
        for canonical_episode in canonical_season.episodes:
            _remember(
                session,
                canonical_episode,
                (str(canonical_season.id), canonical_episode.key),
            )


# TODO: Validate
def canonical_show_by_key(session: Session, key: str) -> Show:
    cache_key = (key,)
    if remembered := _remembered(session, Show, cache_key):
        return remembered

    existing = session.exec(
        select(Show)
        .where(is_canonical(Show), Show.key == key)
        .options(
            selectinload(Show.seasons).selectinload(  # type: ignore[arg-type]
                Season.episodes,  # type: ignore[arg-type]
            ),
        ),
    ).first()
    if existing:
        _remember_title(session, existing)
        return existing
    canonical = Show(key=key)
    session.add(canonical)
    _remember_title(session, canonical)
    return canonical


# TODO: Validate
def canonical_season_by_key(
    session: Session,
    key: str,
    canonical_show_id: uuid.UUID,
) -> Season:
    cache_key = (str(canonical_show_id), key)
    if remembered := _remembered(session, Season, cache_key):
        return remembered

    if canonical_show_id not in _loaded_parents(session):
        existing = session.exec(
            select(Season).where(
                is_canonical(Season),
                Season.show_id == canonical_show_id,
                Season.key == key,
            ),
        ).first()
        if existing:
            _remember(session, existing, cache_key)
            return existing

    canonical = Season(key=key, show_id=canonical_show_id)
    session.add(canonical)
    _remember(session, canonical, cache_key)
    _loaded_parents(session).add(canonical.id)
    return canonical


# TODO: Validate
def canonical_episode_by_key(
    session: Session,
    key: str,
    canonical_season_id: uuid.UUID,
) -> Episode:
    cache_key = (str(canonical_season_id), key)
    if remembered := _remembered(session, Episode, cache_key):
        return remembered

    if canonical_season_id not in _loaded_parents(session):
        existing = session.exec(
            select(Episode).where(
                is_canonical(Episode),
                Episode.season_id == canonical_season_id,
                Episode.key == key,
            ),
        ).first()
        if existing:
            _remember(session, existing, cache_key)
            return existing

    canonical = Episode(key=key, season_id=canonical_season_id)
    session.add(canonical)
    _remember(session, canonical, cache_key)
    return canonical


# TODO: Validate
def link_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> ShowCanonicalShow:
    for link in show.canonical_show_links:
        if link.canonical_show is canonical_show or (
            canonical_show.id is not None
            and link.canonical_show_id == canonical_show.id
        ):
            return link
    link = ShowCanonicalShow(show=show, canonical_show=canonical_show)
    session.add(link)
    return link


# TODO: Validate
def canonical_ids_by_key(
    session: Session,
    keys: Collection[str],
    level: type[Show | Season | Episode],
) -> dict[str, uuid.UUID]:
    if not keys:
        return {}
    canonical_column = {
        Show: Show.canonical_show_id,
        Season: Season.canonical_season_id,
        Episode: Episode.canonical_episode_id,
    }[level]
    rows = session.exec(
        select(level.key, canonical_column).where(  # type: ignore[call-overload]
            col(level.key).in_(keys),
            col(canonical_column).is_not(None),
        ),
    ).all()
    return dict(rows)


# TODO: Validate
def canonical_show_ids_by_key(
    session: Session,
    show_keys: Collection[str],
) -> dict[str, set[uuid.UUID]]:
    if not show_keys:
        return {}
    rows = session.exec(
        select(  # type: ignore[call-overload]
            Show.key,
            ShowCanonicalShow.canonical_show_id,
        )
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Show.id))
        .where(is_copy(Show), col(Show.key).in_(show_keys)),
    ).all()
    canonical_show_ids: dict[str, set[uuid.UUID]] = defaultdict(set)
    for show_key, canonical_show_id in rows:
        canonical_show_ids[show_key].add(canonical_show_id)
    return canonical_show_ids
