# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever one
a `User` picks.
"""

import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlmodel import Session, col, func, select

from app.episodes.models import Episode, UserEpisodeUrl
from app.episodes.schemas import (
    UserEpisodeUrlOutput,
)
from app.users.models import User


# TODO: Validate
def set_episode_url_for_user(
    session: Session,
    episode: Episode,
    current_user: User,
    url: str,
) -> UserEpisodeUrlOutput:
    """Point a `User`'s own copy of an `Episode` at a URL of their choosing."""
    tmdb_episode_id = tmdb_episode_from_url(episode)
    record = set_user_episode_url(session, current_user, tmdb_episode_id, url)
    return UserEpisodeUrlOutput(
        tmdb_episode_id=tmdb_episode_id,
        url=record.url,
    )


# TODO: Validate
def clear_episode_url_for_user(
    session: Session,
    episode: Episode,
    current_user: User,
) -> UserEpisodeUrlOutput:
    """Drop the URL a `User` gave for an `Episode`."""
    tmdb_episode_id = tmdb_episode_from_url(episode)
    clear_user_episode_url(session, current_user, tmdb_episode_id)
    return UserEpisodeUrlOutput(tmdb_episode_id=tmdb_episode_id, url=None)


# TODO: Validate
def user_episode_url(
    session: Session,
    user: User | None,
    tmdb_episode_id: uuid.UUID,
) -> UserEpisodeUrl | None:
    if user is None:
        return None
    return session.get(UserEpisodeUrl, (user.id, tmdb_episode_id))


# TODO: Validate
def set_user_episode_url(
    session: Session,
    user: User,
    tmdb_episode_id: uuid.UUID,
    url: str,
) -> UserEpisodeUrl:
    record = user_episode_url(session, user, tmdb_episode_id)
    if record:
        record.url = url
    else:
        record = UserEpisodeUrl(
            user_id=user.id,
            tmdb_episode_id=tmdb_episode_id,
            url=url,
        )
        session.add(record)
    session.commit()
    session.refresh(record)
    return record


# TODO: Validate
def clear_user_episode_url(
    session: Session,
    user: User,
    tmdb_episode_id: uuid.UUID,
) -> None:
    record = user_episode_url(session, user, tmdb_episode_id)
    if record:
        session.delete(record)
        session.commit()


# TODO: Validate
def user_episode_urls(
    session: Session,
    user: User | None,
    tmdb_episode_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if user is None or not tmdb_episode_ids:
        return {}
    records = session.exec(
        select(UserEpisodeUrl).where(
            UserEpisodeUrl.user_id == user.id,
            col(UserEpisodeUrl.tmdb_episode_id).in_(set(tmdb_episode_ids)),
        ),
    ).all()
    return {record.tmdb_episode_id: record.url for record in records}


# TODO: Validate
def single_tmdb_episode_id(episode: Episode) -> uuid.UUID | None:
    if len(episode.tmdb_episode_ids) > 1:
        return None
    return episode.sole_tmdb_episode_id or episode.id


# TODO: Validate
def tmdb_episode_from_url(episode: Episode) -> uuid.UUID:
    tmdb_episode_id = single_tmdb_episode_id(episode)
    if tmdb_episode_id is None:
        raise HTTPException(
            status_code=422,
            detail="This episode stands for more than one episode.",
        )
    return tmdb_episode_id


# TODO: Validate
def user_episode_url_count(session: Session, user: User) -> int:
    return session.exec(
        select(func.count())
        .select_from(UserEpisodeUrl)
        .where(
            UserEpisodeUrl.user_id == user.id,
        ),
    ).one()
