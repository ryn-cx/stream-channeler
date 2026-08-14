# TODO: Validate
"""The canonical rows TMDB writes, and what each website's rows stand for."""

import uuid
from collections import defaultdict
from collections.abc import Collection

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical, is_non_canonical
from app.canonical_media.keys import tmdb_key_clause
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source


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
    canonical = Show(key=key, source_id=source.id)
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
    """Record that `show` stands for the canonical show `canonical_show`.

    A non-canonical row stands for every canonical show linked to it and no more
    for one than for another, so this adds one to the set and settles nothing
    about which of them the row is chiefly about.
    """
    # If this show is not canonical
    if not canonical_show.is_canonical:
        message = f"{canonical_show} is not a canonical show."
        raise ValueError(message)
    if show.non_canonical_shows:
        message = f"{show} has other shows linked to it."
        raise ValueError(message)

    show.is_canonical = False
    for existing_canonical_show in show.canonical_show_links:
        # By the row where the link is already stored, and by the object itself
        # where it is not: a link made this session names the canonical show it
        # holds rather than its id, which the flush is what writes.
        if (
            existing_canonical_show.canonical_show is canonical_show
            or existing_canonical_show.canonical_show_id == canonical_show.id
        ):
            return existing_canonical_show
    existing_canonical_show = ShowCanonicalShow(
        show=show,
        canonical_show=canonical_show,
    )
    session.add(existing_canonical_show)
    return existing_canonical_show


# TODO: Validate
def _tmdb_episodes(
    session: Session,
    canonical_show_ids: Collection[uuid.UUID],
) -> list[Episode]:
    statement = (
        select(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .where(
            is_canonical(Episode),
            col(Season.show_id).in_(canonical_show_ids),
            tmdb_key_clause(col(Episode.key)),
        )
    )
    return list(session.exec(statement).all())


# TODO: Validate
def _tmdb_episodes_by_name_and_number(
    tmdb_episodes: Collection[Episode],
) -> dict[tuple[str, int], Episode]:
    candidates: dict[tuple[str, int], Episode] = {}
    ambiguous: set[tuple[str, int]] = set()
    for candidate in tmdb_episodes:
        if candidate.name is None or candidate.episode_number is None:
            continue
        pairing = (candidate.name, candidate.episode_number)
        if pairing in candidates:
            ambiguous.add(pairing)
            continue
        candidates[pairing] = candidate
    # Two TMDB episodes sharing a name and a number say nothing about which of
    # them an episode is, so neither is offered.
    for pairing in ambiguous:
        del candidates[pairing]
    return candidates


# TODO: Validate
def match_canonical_episodes(session: Session, show: Show) -> None:
    """Point each episode of `show` at the TMDB episode of the same name and number.

    Only TMDB rows are ever pointed at. An episode TMDB has no record of is left
    pointing at nothing rather than given a canonical row of its own, so a
    canonical episode only ever hangs off a canonical show TMDB holds.

    A film is one episode of one season on both sides, so a row with a single
    episode against a canonical show with a single episode is matched outright:
    there is nothing else either of them could be, whatever the two are named.
    """
    canonical_show_ids = show.canonical_show_ids
    if not canonical_show_ids:
        return

    tmdb_episodes = _tmdb_episodes(session, canonical_show_ids)
    if not tmdb_episodes:
        return

    episodes = [
        episode for season in show.active_children for episode in season.active_children
    ]
    if len(episodes) == 1 and len(tmdb_episodes) == 1:
        only_episode = episodes[0]
        if (
            only_episode.canonical_episode_id is None
            and not only_episode.canonical_episode_locked
        ):
            only_episode.canonical_episode = tmdb_episodes[0]
        return

    candidates = _tmdb_episodes_by_name_and_number(tmdb_episodes)
    if not candidates:
        return

    # One canonical episode is one episode to watch, so a TMDB episode already
    # taken is not handed to a second episode of the same show.
    taken = {episode.canonical_episode_id for episode in episodes}
    for episode in episodes:
        if episode.canonical_episode_id or episode.name is None:
            continue
        if episode.episode_number is None:
            continue
        match = candidates.get((episode.name, episode.episode_number))
        if match is None or match.id in taken:
            continue
        episode.canonical_episode = match
        taken.add(match.id)


# TODO: Validate
def canonical_ids_by_key(
    session: Session,
    keys: Collection[str],
) -> dict[str, uuid.UUID]:
    """Map each episode key to the canonical episode that row stands for.

    Only episodes answer this way. A non-canonical show stands for however many
    canonical shows a website mixed into it and names none of them in a column,
    so a show key is asked of `canonical_show_ids_by_key` and answered with all
    of them.
    """
    if not keys:
        return {}
    rows = session.exec(
        select(Episode.key, Episode.canonical_episode_id).where(
            col(Episode.key).in_(keys),
            col(Episode.canonical_episode_id).is_not(None),
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
