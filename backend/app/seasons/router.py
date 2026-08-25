# TODO: Validate
"""Season router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.canonical_media.metadata import (
    canonical_season_of,
    tmdb_season_url,
)
from app.issue_reports.service import list_season_issue_reports
from app.media.service import delete_record
from app.plugins.dependencies import ExistingPlugin
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import ExistingSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonInformationOutput,
    SeasonInformationSide,
    SeasonListOutput,
    SeasonOutput,
    SeasonsPublic,
    SeasonUpdate,
)
from app.service import list_response
from app.shows.dependencies import ExistingShow
from app.shows.models import Show
from app.sources.dependencies import ExistingSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser

plugin_seasons_router = APIRouter(
    prefix="/plugins/{plugin_id}",
    tags=["seasons"],
    dependencies=[Depends(get_current_active_superuser)],
)
source_seasons_router = APIRouter(
    prefix="/sources/{source_id}",
    tags=["seasons"],
    dependencies=[Depends(get_current_active_superuser)],
)
show_seasons_router = APIRouter(
    prefix="/shows/{show_id}",
    tags=["seasons"],
    dependencies=[Depends(get_current_active_superuser)],
)
seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])

SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


# TODO: Validate
@show_seasons_router.post("/seasons")
def create_season(
    session: SessionDep,
    show: ExistingShow,
    season_input: SeasonCreate,
) -> SeasonOutput:
    return SeasonOutput.model_validate(season_input.create(session, Season, show))


# TODO: Validate
@seasons_router.get("", dependencies=[Depends(get_current_active_superuser)])
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get `Season`s."""
    seasons = list_response(
        session=session,
        base=Season.select_with_plugin_eager(),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    return seasons


# TODO: Validate
@show_seasons_router.get("/seasons")
def get_show_seasons(
    session: SessionDep,
    show: ExistingShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    seasons = list_response(
        session=session,
        base=Season.select_with_plugin_eager().where(Season.show_id == show.id),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    return seasons


# TODO: Validate
@plugin_seasons_router.get("/seasons")
def get_plugin_seasons(
    session: SessionDep,
    plugin: ExistingPlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    seasons = list_response(
        session=session,
        base=Season.select_with_plugin_eager().where(Source.plugin_id == plugin.id),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    return seasons


# TODO: Validate
@source_seasons_router.get("/seasons")
def get_source_seasons(
    session: SessionDep,
    source: ExistingSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    seasons = list_response(
        session=session,
        base=Season.select_with_plugin_eager().where(Show.source_id == source.id),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    return seasons


# TODO: Validate
def _information_side(
    label: str,
    season: Season,
    show: Show,
    url: str | None,
) -> SeasonInformationSide:
    return SeasonInformationSide(
        label=label,
        name=season.name,
        season_number=season.season_number,
        sort_order=season.sort_order,
        image_url=season.image_url,
        show_name=show.name,
        url=url,
        key=season.key,
    )


# TODO: Validate
@seasons_router.get("/{season_id}/information")  # noqa: FAST003 - Used by ExistingSeason.
def get_season_information(
    session: SessionDep,
    season: ExistingSeason,
) -> SeasonInformationOutput:
    """Return what the website and TMDB each say about a `Season`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    show = season.show
    source = show.source

    counterpart = canonical_season_of(session, season.id)
    tmdb: SeasonInformationSide | None = None
    if counterpart:
        canonical_season, canonical_show = counterpart
        tmdb = _information_side(
            TMDB_PLUGIN_KEY,
            canonical_season,
            canonical_show,
            tmdb_season_url(canonical_show.key, canonical_season.season_number),
        )

    return SeasonInformationOutput(
        season_id=season.id,
        issue_reports=list_season_issue_reports(session, season.id),
        source=_information_side(
            source.name or source.plugin.name or source.plugin.key,
            season,
            show,
            season.url,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
@seasons_router.get(
    "/{season_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def get_season(season: ExistingSeason) -> SeasonOutput:
    return SeasonOutput.model_validate(season)


# TODO: Validate
@seasons_router.patch(
    "/{season_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def update_season(
    session: SessionDep,
    season: ExistingSeason,
    season_input: SeasonUpdate,
) -> SeasonOutput:
    return SeasonOutput.model_validate(season_input.update(session, season))


# TODO: Validate
@seasons_router.delete(
    "/{season_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_season(session: SessionDep, season: ExistingSeason) -> Message:
    return delete_record(session, season)


router = APIRouter()
router.include_router(seasons_router)
router.include_router(show_seasons_router)
router.include_router(source_seasons_router)
router.include_router(plugin_seasons_router)
