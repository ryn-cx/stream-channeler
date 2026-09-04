# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import watch_identifier
from app.canonical_media.service.cache import (
    _loaded_parents,
    _remember,
    _remember_title,
    _remembered,
)
from app.episodes.models import Episode
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
        _remember_title(session, existing)
        return existing
    # The row it hangs off is set as the record and not only as the id, because
    # a row minted here is read back before anything is written and a pending
    # row answers for the record it hangs off with nothing at all.
    canonical = Show(key=key, source_id=source.id)
    canonical.source = source
    session.add(canonical)
    _remember_title(session, canonical)
    return canonical


# TODO: Validate
def canonical_season_by_key(
    session: Session,
    key: str,
    canonical_show: Show,
) -> Season:
    cache_key = (str(canonical_show.id), key)
    if remembered := _remembered(session, Season, cache_key):
        return remembered

    if canonical_show.id not in _loaded_parents(session):
        existing = session.exec(
            select(Season).where(
                Season.show_id == canonical_show.id,
                Season.key == key,
            ),
        ).first()
        if existing:
            _remember(session, existing, cache_key)
            return existing

    canonical = Season(key=key, show_id=canonical_show.id)
    canonical.show = canonical_show
    session.add(canonical)
    _remember(session, canonical, cache_key)
    _loaded_parents(session).add(canonical.id)
    return canonical


# TODO: Validate
def _episode_moved_season(
    session: Session,
    key: str,
    canonical_season: Season,
) -> Episode | None:
    moved = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_canonical(Episode),
            Episode.key == key,
            Season.show_id == canonical_season.show_id,
        ),
    ).first()
    if moved is None:
        return None

    if moved.season is canonical_season:
        return moved

    moved.season = canonical_season
    moved.season_id = canonical_season.id
    session.add(moved)
    return moved


# TODO: Validate
def canonical_episode_by_key(
    session: Session,
    key: str,
    canonical_season: Season,
    plugin_key: str,
) -> Episode:
    """Return the canonical episode for this key, creating one where there is none.

    `plugin_key` is who issued `key`, and is asked for rather than reached
    through the season because it is what a `Watch` is matched on. A row created
    without it would be a row no watch could ever name.
    """
    cache_key = (str(canonical_season.id), key)
    if remembered := _remembered(session, Episode, cache_key):
        return remembered

    if canonical_season.id not in _loaded_parents(session):
        existing = session.exec(
            select(Episode).where(
                is_canonical(Episode),
                Episode.season_id == canonical_season.id,
                Episode.key == key,
            ),
        ).first()
        if existing:
            _remember(session, existing, cache_key)
            return existing

    if moved := _episode_moved_season(session, key, canonical_season):
        _remember(session, moved, cache_key)
        return moved

    canonical = Episode(
        key=key,
        season_id=canonical_season.id,
        watch_identifier=watch_identifier(plugin_key, key),
    )
    canonical.season = canonical_season
    session.add(canonical)
    _remember(session, canonical, cache_key)
    return canonical
