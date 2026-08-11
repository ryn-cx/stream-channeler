# TODO: Validate
"""Season router."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.issue_reports.service import list_season_issue_reports
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.media.tmdb_fallback import (
    TMDB_PLUGIN_KEY,
    fill_seasons,
    tmdb_season_counterpart,
    tmdb_season_url,
)
from app.media.tmdb_identifier_links import check_season_identifier
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
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


# TODO: Validate
def _season_output(session: SessionDep, season: Season) -> SeasonOutput:
    """Return a `Season` with whatever its website left out taken from TMDB."""
    return fill_seasons(session, [SeasonOutput.model_validate(season)])[0]


# TODO: Validate
@show_seasons_router.post("/seasons")
def create_season(
    session: SessionDep,
    show: EditableShow,
    season_input: SeasonCreate,
) -> SeasonOutput:
    """Create a `Season` if the `Show` is editable by the `User`.

    A `season_identifier` naming a TMDB season is checked before it is stored,
    and the title holding it is imported for the link to read.
    """
    check_season_identifier(
        session,
        season_input.season_identifier,
        show.show_identifier,
    )
    return _season_output(session, season_input.create(session, Season, show))


# TODO: Validate
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


# TODO: Validate
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


# TODO: Validate
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


# TODO: Validate
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
@seasons_router.get("/{season_id}/information")  # noqa: FAST003 - Used by ReadableSeason.
def get_season_information(
    session: SessionDep,
    season: ReadableSeason,
) -> SeasonInformationOutput:
    """Return what the website and TMDB each say about a `Season`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    show = season.show
    source = show.source

    counterpart = tmdb_season_counterpart(session, season.season_identifier)
    tmdb: SeasonInformationSide | None = None
    if counterpart:
        tmdb_season, tmdb_show = counterpart
        tmdb = _information_side(
            TMDB_PLUGIN_KEY,
            tmdb_season,
            tmdb_show,
            tmdb_season_url(tmdb_show.key, tmdb_season.season_number),
        )

    return SeasonInformationOutput(
        season_id=season.id,
        season_identifier=season.season_identifier,
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
@seasons_router.get("/{season_id}")  # noqa: FAST003 - Used by ReadableSeason.
def get_season(session: SessionDep, season: ReadableSeason) -> SeasonOutput:
    """Get a `Season` if it's readable by the `User`."""
    return _season_output(session, season)


# TODO: Validate
@seasons_router.patch("/{season_id}")  # noqa: FAST003 - Used by EditableSeason.
def update_season(
    session: SessionDep,
    season: EditableSeason,
    season_input: SeasonUpdate,
) -> SeasonOutput:
    """Update and return a `Season` if it's editable by the `User`.

    A `season_identifier` naming a different TMDB season repoints every
    `Episode` at TMDB, so their identifiers follow the season the `User` chose.
    The `season_identifier` itself is what they asked for, so it is left alone.

    A new `season_identifier` naming a TMDB season is checked before it is
    stored, so a season the title does not have is refused rather than kept as a
    link to nothing, and the title is imported for the link to read.
    """
    previous_tmdb_id = season.tmdb_id
    if (
        season_input.season_identifier is not None
        and season_input.season_identifier != season.season_identifier
    ):
        check_season_identifier(
            session,
            season_input.season_identifier,
            season.show.show_identifier,
        )
    season = season_input.update(session, season)
    if season.tmdb_id != previous_tmdb_id:
        relink_season_children(session, season)
    return _season_output(session, season)


# TODO: Validate
@seasons_router.delete("/{season_id}")  # noqa: FAST003 - Used by EditableSeason.
def delete_season(session: SessionDep, season: EditableSeason) -> Message:
    """Delete a `Season` if it's editable by the `User`."""
    return delete_record(session, season)


router = APIRouter()
router.include_router(seasons_router)
router.include_router(show_seasons_router)
router.include_router(source_seasons_router)
router.include_router(plugin_seasons_router)
