# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show


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
