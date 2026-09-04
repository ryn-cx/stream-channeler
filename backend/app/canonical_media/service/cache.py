# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

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
