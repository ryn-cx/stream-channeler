# TODO: Validate
import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.utils import tz_datetime


# TODO: Validate
def ignore_episode(session: Session, episode: Episode) -> Episode:
    if episode.ignored_at is None:
        episode.ignored_at = tz_datetime.now()
        session.add(episode)
        session.commit()
        session.refresh(episode)
    return episode


# TODO: Validate
def unignore_episode(session: Session, episode: Episode) -> Episode:
    if episode.ignored_at is not None:
        episode.ignored_at = None
        session.add(episode)
        session.commit()
        session.refresh(episode)
    return episode


# TODO: Validate
def ignore_episodes(
    session: Session,
    episode_ids: Sequence[uuid.UUID],
) -> list[Episode]:
    return [
        ignore_episode(session, _existing_episode(session, episode_id))
        for episode_id in episode_ids
    ]


# TODO: Validate
def _existing_episode(session: Session, episode_id: uuid.UUID) -> Episode:
    episode = session.exec(
        select(Episode).where(col(Episode.id) == episode_id),
    ).first()
    if episode is None:
        raise HTTPException(status_code=404, detail="Episode not found")
    return episode
