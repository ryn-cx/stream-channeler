# TODO: Validate

import re
import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
    EpisodeTmdbEpisode,
)
from app.episodes.schemas import EpisodeTmdbLinkInput
from app.seasons.models import Season
from app.titles.models import Title
from app.titles.service.linking import old_link_title_to_tmdb
from app.tmdb_media.filters import is_not_linked
from app.utils import tz_datetime
from plugins.TMDB import TMDB

_TMDB_EPISODE_URL = re.compile(
    r"themoviedb\.org/tv/(?P<tmdb_id>\d+)[^/]*"
    r"/season/(?P<season_number>\d+)/episode/(?P<episode_number>\d+)",
)
_TMDB_MOVIE_URL = re.compile(r"themoviedb\.org/movie/(?P<tmdb_id>\d+)")


# TODO: Validate
def _import_tmdb_url(session: Session, url: str) -> Title:
    imported = TMDB(session).validate_and_import_url(url)
    return imported[0].title


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
    tmdb_title = _import_tmdb_url(session, url)
    tmdb_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(
            is_not_linked(Episode),
            Season.title_id == tmdb_title.id,
            Season.season_number == int(found["season_number"]),
            Episode.episode_number == int(found["episode_number"]),
        ),
    ).one()
    return link_episode(session, episode, tmdb_episode)


# TODO: Validate
def _link_episode_using_tmdb_movie(
    session: Session,
    episode: Episode,
    url: str,
) -> Episode:
    tmdb_title = _import_tmdb_url(session, url)

    tmdb_episode = session.exec(
        select(Episode)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .where(is_not_linked(Episode), Season.title_id == tmdb_title.id),
    ).one()
    return link_episode(session, episode, tmdb_episode)


# TODO: Validate
def link_episode(
    session: Session,
    episode: Episode,
    tmdb_episode: Episode,
) -> Episode:
    for same_media in _episodes_sharing_identifier(session, episode):
        _link_one_episode(session, same_media, tmdb_episode)

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
    tmdb_episode: Episode,
) -> None:
    old_link_title_to_tmdb(
        session,
        episode.season.title,
        tmdb_episode.season.title,
        note=f"{MANUAL_NOTE_PREFIX}Episode selection",
    )

    note = f"{MANUAL_NOTE_PREFIX}Selection"
    existing_link = next(
        (
            link
            for link in episode.tmdb_episode_links
            if link.tmdb_episode_id == tmdb_episode.id
        ),
        None,
    )
    if existing_link is None:
        session.add(
            EpisodeTmdbEpisode(
                episode_id=episode.id,
                tmdb_episode_id=tmdb_episode.id,
                note=note,
                manual_tmdb_link=True,
            ),
        )
    else:
        existing_link.note = note
        existing_link.manual_tmdb_link = True
        session.add(existing_link)

    episode.tmdb_episode_validated_at = tz_datetime.now()
    session.add(episode)


# TODO: Validate
def _drop_links(
    session: Session,
    episode: Episode,
    tmdb_episode: Episode | None = None,
) -> None:
    for link in list(episode.tmdb_episode_links):
        if (
            tmdb_episode is None
            or link.tmdb_episode_id == tmdb_episode.id
        ):
            session.delete(link)
    session.flush()
    session.expire(episode, ["tmdb_episode_links", "is_linked"])


# TODO: Validate
def unlink_episode(
    session: Session,
    episode: Episode,
    tmdb_episode: Episode | None = None,
) -> Episode:
    _drop_links(session, episode, tmdb_episode)

    if not episode.tmdb_episode_links:
        episode.tmdb_episode_validated_at = None
        session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def quick_unlink_episode(session: Session, episode: Episode) -> Episode:
    _drop_links(session, episode)

    episode.tmdb_episode_validated_at = None
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def verify_tmdb_link(session: Session, episode: Episode) -> Episode:
    """Settle the links an `Episode` already carries as the right ones.

    Nothing about what it stands for changes: the links an automatic match made
    are taken as correct and locked so no later import moves them.
    """
    if not episode.tmdb_episode_links:
        raise HTTPException(
            status_code=400,
            detail="The episode is linked to nothing to be verified against",
        )

    episode.tmdb_episode_validated_at = tz_datetime.now()
    for link in episode.tmdb_episode_links:
        link.note = f"{MANUAL_NOTE_PREFIX}Verified"
        link.manual_tmdb_link = True
        session.add(link)
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return episode


# TODO: Validate
def mark_episode_absent_from_tmdb(session: Session, episode: Episode) -> Episode:
    _drop_links(session, episode)

    episode.tmdb_episode_validated_at = tz_datetime.now()
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
def _existing_tmdb_episode(
    session: Session,
    tmdb_episode_id: uuid.UUID,
) -> Episode:
    tmdb_episode = session.exec(
        select(Episode).where(
            is_not_linked(Episode),
            col(Episode.id) == tmdb_episode_id,
        ),
    ).first()
    if tmdb_episode is None:
        raise HTTPException(status_code=404, detail="Canonical episode not found")
    return tmdb_episode


# TODO: Validate
def link_episodes(
    session: Session,
    links: Sequence[EpisodeTmdbLinkInput],
) -> list[Episode]:
    return [
        link_episode(
            session,
            _existing_episode(session, link.episode_id),
            _existing_tmdb_episode(session, link.tmdb_episode_id),
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
