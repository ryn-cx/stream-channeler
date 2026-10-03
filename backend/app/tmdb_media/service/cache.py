# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title


# TODO: Validate
def _cache[TmdbT: Title | Season | Episode](
    session: Session,
    model: type[TmdbT],
) -> dict[tuple[str, ...], TmdbT]:
    cache: dict[tuple[str, ...], TmdbT] = session.info.setdefault(
        model.__name__,
        {},
    )
    return cache


# TODO: Validate
def _remembered[TmdbT: Title | Season | Episode](
    session: Session,
    model: type[TmdbT],
    cache_key: tuple[str, ...],
) -> TmdbT | None:
    remembered = _cache(session, model).get(cache_key)
    if remembered is None or remembered not in session:
        return None
    return remembered


# TODO: Validate
def _remember(
    session: Session,
    canonical: Title | Season | Episode,
    cache_key: tuple[str, ...],
) -> None:
    _cache(session, type(canonical))[cache_key] = canonical
