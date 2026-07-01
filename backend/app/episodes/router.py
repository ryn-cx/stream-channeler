"""Episodes router."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import EditableEpisode, ReadableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeUpdate,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_list_response,
    media_owner_list_response,
)
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.dependencies import OptionalUser

season_episodes_router = APIRouter(prefix="/seasons/{season_id}", tags=["episodes"])
episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])


@season_episodes_router.post("/episodes", response_model=EpisodeOutput)
def create_episode(
    session: SessionDep,
    season: EditableSeason,
    episode_input: EpisodeCreate,
) -> Episode:
    """Create an `Episode` if the `Season` is editable by the `User`."""
    return episode_input.create(session, Episode, season)


@episodes_router.get("")
def get_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s readable by the `User`."""
    return media_owner_list_response(
        session=session,
        base=select(Episode).join(Season).join(Show).join(Source).join(Plugin),
        response_model=EpisodesPublic,
        schema=EpisodeOutput,
        read_options=read_options,
        current_user=current_user,
    )


@season_episodes_router.get("/episodes")
def get_season_episodes(
    session: SessionDep,
    season: ReadableSeason,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Season` if it is readable by the `User`."""
    base = select(Episode).where(Episode.season_id == season.id)
    return media_list_response(
        session=session,
        base=base,
        response_model=EpisodesPublic,
        schema=EpisodeOutput,
        params=read_options,
        current_user=current_user,
    )


@episodes_router.get("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by ReadableEpisode
def get_episode(episode: ReadableEpisode) -> Episode:
    """Get an `Episode` if it's readable by the `User`."""
    return episode


@episodes_router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by EditableEpisode
def update_episode(
    session: SessionDep,
    episode: EditableEpisode,
    episode_input: EpisodeUpdate,
) -> Episode:
    """Update and return an `Episode` if it's editable by the `User`."""
    return episode_input.update(session, episode)


@episodes_router.delete("/{episode_id}")  # noqa: FAST003 - Used by EditableEpisode
def delete_episode(session: SessionDep, episode: EditableEpisode) -> Message:
    """Delete an `Episode` if it's editable by the `User`."""
    return delete_record(session, episode)


router = APIRouter()
router.include_router(episodes_router)
router.include_router(season_episodes_router)
