# TODO: Validate
"""Dependencies for media."""

import uuid
from typing import Annotated

from fastapi import Body, Depends, HTTPException, Path
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.models import Episode, EpisodeWatch, Season, Show, Source
from app.media.schemas import EpisodeWatchPostInput


def get_existing_episode_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode_watch_id: Annotated[uuid.UUID, Path()],
) -> EpisodeWatch:
    """Get an episode watch entry if the user owns it.

    The Episode, Season, Show, Source, and Plugin relationships are eagerly loaded.

    Args:
        session: Database session.
        current_user: Current authenticated user.
        episode_watch_id: Episode watch ID.

    Returns:
        EpisodeWatch with Episode, Season, Show, Source, and Plugin relationships
        loaded.

    Raises:
        HTTPException: 404 if episode watch is not found, 403 if user is not authorized.
    """
    episode_watch = session.exec(
        select(EpisodeWatch)
        .options(
            joinedload(EpisodeWatch.episode)
            .joinedload(Episode.season)
            .joinedload(Season.show)
            .joinedload(Show.source)
            .joinedload(Source.plugin),
        )
        .where(EpisodeWatch.id == episode_watch_id),
    ).first()

    if not (episode_watch):
        raise HTTPException(status_code=404, detail="Episode watch not found")

    if episode_watch.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return episode_watch


ExistingEpisodeWatch = Annotated[EpisodeWatch, Depends(get_existing_episode_watch)]


def get_existing_episode(
    session: SessionDep,
    watch_input: Annotated[EpisodeWatchPostInput, Body()],
) -> Episode:
    """Get an episode if it exists.

    Args:
        session: Database session.
        watch_input: Episode watch input containing episode_id.

    Returns:
        Episode with Season, Show, Source, and Plugin relationships loaded.

    Raises:
        HTTPException: 404 if episode is not found.
    """
    episode = session.exec(
        select(Episode)
        .options(
            joinedload(Episode.season)
            .joinedload(Season.show)
            .joinedload(Show.source)
            .joinedload(Source.plugin),
        )
        .where(Episode.id == watch_input.episode_id),
    ).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    return episode


ExistingEpisode = Annotated[Episode, Depends(get_existing_episode)]
