# TODO: Validate

import re

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.service import add_canonical_show
from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
    EpisodeCanonicalEpisode,
)
from app.seasons.models import Season
from app.shows.models import Show

_TMDB_EPISODE_URL = re.compile(
    r"themoviedb\.org/tv/(?P<tmdb_id>\d+)[^/]*"
    r"/season/(?P<season_number>\d+)/episode/(?P<episode_number>\d+)",
)
_TMDB_MOVIE_URL = re.compile(r"themoviedb\.org/movie/(?P<tmdb_id>\d+)")


# TODO: Validate
def _import_tmdb_url(session: Session, url: str) -> Show:
    from plugins.TMDB import TMDB  # noqa: PLC0415

    imported = TMDB(session).import_url(url)
    statement = select(Show).where(
        is_canonical(Show),
        Show.key == imported[0].show_key,
    )
    return session.exec(statement).one()


# TODO: Validate
def link_episode_using_tmdb_url(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    address = url.strip()
    if found := _TMDB_EPISODE_URL.search(address):
        return _link_episode_using_tmdb_episode(session, episode, address, found)
    if _TMDB_MOVIE_URL.search(address):
        return _link_episode_using_tmdb_movie(session, episode, address)

    raise HTTPException(
        status_code=400,
        detail=f"{url} is not the address of a TMDB film or series episode",
    )


# TODO: Validate
def _link_episode_using_tmdb_episode(
    session: Session,
    episode: Episode,
    url: str,
    found: re.Match[str],
) -> Episode:
    canonical_show = _import_tmdb_url(session, url)
    canonical_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_canonical(Episode),
            Season.show_id == canonical_show.id,
            Season.season_number == int(found["season_number"]),
            Episode.episode_number == int(found["episode_number"]),
        ),
    ).one()
    return link_episode(session, episode, canonical_episode)


# TODO: Validate
def _link_episode_using_tmdb_movie(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    canonical_show = _import_tmdb_url(session, url)

    canonical_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(is_canonical(Episode), Season.show_id == canonical_show.id),
    ).one()
    return link_episode(session, episode, canonical_episode)


# TODO: Validate
def link_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode,
) -> Episode:
    for same_media in _episodes_sharing_identifier(session, episode):
        _link_one_episode(session, same_media, canonical_episode)

    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def _episodes_sharing_identifier(session: Session, episode: Episode) -> list[Episode]:
    return list(
        session.exec(
            select(Episode).where(
                Episode.watch_identifier == episode.watch_identifier,
                col(Episode.deleted_at).is_(None),
            ),
        ).all(),
    )


# TODO: Validate
def _link_one_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode,
) -> None:
    add_canonical_show(session, episode.season.show, canonical_episode.season.show)

    if canonical_episode.id not in episode.canonical_episode_ids:
        session.add(
            EpisodeCanonicalEpisode(
                episode_id=episode.id,
                canonical_episode_id=canonical_episode.id,
                sort_order=episode.sort_order,
            ),
        )

    episode.is_canonical = False
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Selection"
    session.add(episode)


# TODO: Validate
def _drop_links(
    session: Session,
    episode: Episode,
    canonical_episode: Episode | None = None,
) -> None:
    for link in list(episode.canonical_episode_links):
        if (
            canonical_episode is None
            or link.canonical_episode_id == canonical_episode.id
        ):
            session.delete(link)
    session.flush()
    session.expire(episode, ["canonical_episode_links"])


# TODO: Validate
def unlink_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode | None = None,
) -> Episode:
    _drop_links(session, episode, canonical_episode)

    if not episode.canonical_episode_links:
        episode.is_canonical = True
        episode.canonical_episode_locked = False
        episode.canonical_episode_note = None
        session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def mark_episode_absent_from_tmdb(session: Session, episode: Episode) -> Episode:
    _drop_links(session, episode)

    episode.is_canonical = True
    episode.canonical_episode_locked = True
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Not on TMDB"
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode
