# TODO: Validate

import re
import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.service import add_canonical_show
from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
    EpisodeCanonicalEpisode,
)
from app.episodes.schemas import EpisodeCanonicalLinkInput
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime

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
    add_canonical_show(
        session,
        episode.season.show,
        canonical_episode.season.show,
        note=f"{MANUAL_NOTE_PREFIX}Episode selection",
    )

    if canonical_episode.id not in episode.canonical_episode_ids:
        session.add(
            EpisodeCanonicalEpisode(
                episode_id=episode.id,
                canonical_episode_id=canonical_episode.id,
                sort_order=episode.sort_order,
            ),
        )

    episode.canonical_episode_validated_at = tz_datetime.now()
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
    session.expire(episode, ["canonical_episode_links", "is_canonical"])


# TODO: Validate
def unlink_episode(
    session: Session,
    episode: Episode,
    canonical_episode: Episode | None = None,
) -> Episode:
    _drop_links(session, episode, canonical_episode)

    if not episode.canonical_episode_links:
        episode.canonical_episode_validated_at = None
        episode.canonical_episode_note = None
        session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def verify_canonical_link(session: Session, episode: Episode) -> Episode:
    """Settle the links an `Episode` already carries as the right ones.

    Nothing about what it stands for changes: the links an automatic match made
    are taken as correct and locked so no later import moves them.
    """
    if not episode.canonical_episode_links:
        raise HTTPException(
            status_code=400,
            detail="The episode is linked to nothing to be verified against",
        )

    episode.canonical_episode_validated_at = tz_datetime.now()
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Verified"
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def mark_episode_absent_from_tmdb(session: Session, episode: Episode) -> Episode:
    _drop_links(session, episode)

    episode.canonical_episode_validated_at = tz_datetime.now()
    episode.canonical_episode_note = f"{MANUAL_NOTE_PREFIX}Not on TMDB"
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def _existing_episode(session: Session, episode_id: uuid.UUID) -> Episode:
    episode = session.exec(
        select(Episode).where(col(Episode.id) == episode_id),
    ).first()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode


# TODO: Validate
def _existing_canonical_episode(
    session: Session,
    canonical_episode_id: uuid.UUID,
) -> Episode:
    canonical_episode = session.exec(
        select(Episode).where(
            is_canonical(Episode),
            col(Episode.id) == canonical_episode_id,
        ),
    ).first()
    if canonical_episode is None:
        raise HTTPException(status_code=404, detail="Canonical episode not found")
    return canonical_episode


# TODO: Validate
def link_episodes(
    session: Session,
    links: Sequence[EpisodeCanonicalLinkInput],
) -> list[Episode]:
    return [
        link_episode(
            session,
            _existing_episode(session, link.episode_id),
            _existing_canonical_episode(session, link.canonical_episode_id),
        )
        for link in links
    ]


# TODO: Validate
def mark_episodes_absent_from_tmdb(
    session: Session,
    episode_ids: Sequence[uuid.UUID],
) -> list[Episode]:
    return [
        mark_episode_absent_from_tmdb(session, _existing_episode(session, episode_id))
        for episode_id in episode_ids
    ]
