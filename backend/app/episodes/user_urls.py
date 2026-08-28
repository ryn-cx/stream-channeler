# TODO: Validate
import uuid
from collections.abc import Sequence

from fastapi import HTTPException
from sqlmodel import Session, col, func, select

from app.episodes.models import Episode, UserEpisodeUrl
from app.users.models import User


# TODO: Validate
def user_episode_url(
    session: Session,
    user: User | None,
    canonical_episode_id: uuid.UUID,
) -> UserEpisodeUrl | None:
    if user is None:
        return None
    return session.get(UserEpisodeUrl, (user.id, canonical_episode_id))


# TODO: Validate
def set_user_episode_url(
    session: Session,
    user: User,
    canonical_episode_id: uuid.UUID,
    url: str,
) -> UserEpisodeUrl:
    record = user_episode_url(session, user, canonical_episode_id)
    if record:
        record.url = url
    else:
        record = UserEpisodeUrl(
            user_id=user.id,
            canonical_episode_id=canonical_episode_id,
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
    canonical_episode_id: uuid.UUID,
) -> None:
    record = user_episode_url(session, user, canonical_episode_id)
    if record:
        session.delete(record)
        session.commit()


# TODO: Validate
def user_episode_urls(
    session: Session,
    user: User | None,
    canonical_episode_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if user is None or not canonical_episode_ids:
        return {}
    records = session.exec(
        select(UserEpisodeUrl).where(
            UserEpisodeUrl.user_id == user.id,
            col(UserEpisodeUrl.canonical_episode_id).in_(set(canonical_episode_ids)),
        ),
    ).all()
    return {record.canonical_episode_id: record.url for record in records}


# TODO: Validate
def single_canonical_episode_id(episode: Episode) -> uuid.UUID | None:
    if len(episode.canonical_episode_ids) > 1:
        return None
    return episode.sole_canonical_episode_id or episode.id


# TODO: Validate
def canonical_episode_for_url(episode: Episode) -> uuid.UUID:
    canonical_episode_id = single_canonical_episode_id(episode)
    if canonical_episode_id is None:
        raise HTTPException(
            status_code=422,
            detail="This episode stands for more than one episode.",
        )
    return canonical_episode_id


# TODO: Validate
def user_episode_url_count(session: Session, user: User) -> int:
    return session.exec(
        select(func.count())
        .select_from(UserEpisodeUrl)
        .where(
            UserEpisodeUrl.user_id == user.id,
        ),
    ).one()
