"""Episodes router."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.episodes.dependencies import EditableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeListOutput,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeUpdate,
)
from app.media.schemas import MediaReadOptions
from app.media.service import delete_record, media_scoped_list_response
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
from app.seasons.models import Season
from app.service import list_response
from app.shows.dependencies import ReadableShow
from app.shows.models import Show
from app.sources.dependencies import ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_episodes_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["episodes"])
source_episodes_router = APIRouter(prefix="/sources/{source_id}", tags=["episodes"])
show_episodes_router = APIRouter(prefix="/shows/{show_id}", tags=["episodes"])
season_episodes_router = APIRouter(prefix="/seasons/{season_id}", tags=["episodes"])
episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])

EPISODE_EXTRA_COLUMNS: dict[str, Any] = {
    "username": User.username,
    "season_name": Season.name,
    "show_id": Season.show_id,
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


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
    """Get `Episode`s."""
    return media_scoped_list_response(
        session=session,
        base=Episode.select_with_user_eager(),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )


@season_episodes_router.get("/episodes")
def get_season_episodes(
    session: SessionDep,
    season: ReadableSeason,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Season` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Episode.season_id == season.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )


@plugin_episodes_router.get("/episodes")
def get_plugin_episodes(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Plugin` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Source.plugin_id == plugin.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )


@source_episodes_router.get("/episodes")
def get_source_episodes(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Source` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Show.source_id == source.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )


@show_episodes_router.get("/episodes")
def get_show_episodes(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """Get all of the `Episode`s for a `Show` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Episode.select_with_user_eager().where(Season.show_id == show.id),
        response_model=EpisodesPublic,
        schema=EpisodeListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=EPISODE_EXTRA_COLUMNS,
    )


@episodes_router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by EditableEpisode.
def update_episode(
    session: SessionDep,
    episode: EditableEpisode,
    episode_input: EpisodeUpdate,
) -> Episode:
    """Update and return an `Episode` if it's editable by the `User`."""
    return episode_input.update(session, episode)


@episodes_router.delete("/{episode_id}")  # noqa: FAST003 - Used by EditableEpisode.
def delete_episode(session: SessionDep, episode: EditableEpisode) -> Message:
    """Delete an `Episode` if it's editable by the `User`."""
    return delete_record(session, episode)


router = APIRouter()
router.include_router(episodes_router)
router.include_router(season_episodes_router)
router.include_router(show_episodes_router)
router.include_router(source_episodes_router)
router.include_router(plugin_episodes_router)
