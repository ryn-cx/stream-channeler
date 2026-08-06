# TODO: Validate
"""Season router."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.media.tmdb_fallback import fill_seasons
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonListOutput,
    SeasonOutput,
    SeasonsPublic,
    SeasonUpdate,
)
from app.service import list_response
from app.shows.dependencies import EditableShow, ReadableShow
from app.shows.models import Show
from app.shows.service import relink_season_children
from app.sources.dependencies import ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_seasons_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["seasons"])
source_seasons_router = APIRouter(prefix="/sources/{source_id}", tags=["seasons"])
show_seasons_router = APIRouter(prefix="/shows/{show_id}", tags=["seasons"])
seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])

SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "username": User.username,
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


def _season_output(session: SessionDep, season: Season) -> SeasonOutput:
    """Return a `Season` with whatever its website left out taken from TMDB."""
    return fill_seasons(session, [SeasonOutput.model_validate(season)])[0]


@show_seasons_router.post("/seasons")
def create_season(
    session: SessionDep,
    show: EditableShow,
    season_input: SeasonCreate,
) -> SeasonOutput:
    """Create a `Season` if the `Show` is editable by the `User`."""
    return _season_output(session, season_input.create(session, Season, show))


@seasons_router.get("")
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SeasonsPublic:
    """Get `Season`s."""
    seasons = media_scoped_list_response(
        session=session,
        base=Season.select_with_user_eager(),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    fill_seasons(session, seasons.data)
    return seasons


@show_seasons_router.get("/seasons")
def get_show_seasons(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get all of the `Season`s for a `Show` if it is readable by the `User`."""
    seasons = list_response(
        session=session,
        base=Season.select_with_user_eager().where(Season.show_id == show.id),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    fill_seasons(session, seasons.data)
    return seasons


@plugin_seasons_router.get("/seasons")
def get_plugin_seasons(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get all of the `Season`s for a `Plugin` if it is readable by the `User`."""
    seasons = list_response(
        session=session,
        base=Season.select_with_user_eager().where(Source.plugin_id == plugin.id),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    fill_seasons(session, seasons.data)
    return seasons


@source_seasons_router.get("/seasons")
def get_source_seasons(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get all of the `Season`s for a `Source` if it is readable by the `User`."""
    seasons = list_response(
        session=session,
        base=Season.select_with_user_eager().where(Show.source_id == source.id),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    fill_seasons(session, seasons.data)
    return seasons


@seasons_router.get("/{season_id}")  # noqa: FAST003 - Used by ReadableSeason.
def get_season(session: SessionDep, season: ReadableSeason) -> SeasonOutput:
    """Get a `Season` if it's readable by the `User`."""
    return _season_output(session, season)


@seasons_router.patch("/{season_id}")  # noqa: FAST003 - Used by EditableSeason.
def update_season(
    session: SessionDep,
    season: EditableSeason,
    season_input: SeasonUpdate,
) -> SeasonOutput:
    """Update and return a `Season` if it's editable by the `User`.

    A new `tmdb_id` repoints every `Episode` at TMDB so their `tmdb_id` and
    `episode_identifier` follow the one the `User` chose.
    """
    previous_tmdb_id = season.tmdb_id
    season = season_input.update(session, season)
    if season.tmdb_id != previous_tmdb_id:
        relink_season_children(session, season)
    return _season_output(session, season)


@seasons_router.delete("/{season_id}")  # noqa: FAST003 - Used by EditableSeason.
def delete_season(session: SessionDep, season: EditableSeason) -> Message:
    """Delete a `Season` if it's editable by the `User`."""
    return delete_record(session, season)


router = APIRouter()
router.include_router(seasons_router)
router.include_router(show_seasons_router)
router.include_router(source_seasons_router)
router.include_router(plugin_seasons_router)
