# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.service.cache import (
    _remember,
    _remembered,
)
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


# TODO: Validate
def canonical_show_by_key(session: Session, key: str, source: Source) -> Show:
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
        _remember(session, existing, cache_key)
        return existing
    # The row it hangs off is set as the record and not only as the id, because
    # a row minted here is read back before anything is written and a pending
    # row answers for the record it hangs off with nothing at all.
    canonical = Show(key=key, source_id=source.id)
    canonical.source = source
    session.add(canonical)
    _remember(session, canonical, cache_key)
    return canonical
