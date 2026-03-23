import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlmodel import select

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput, EpisodesListOutput
from app.models import Message
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput, PluginsListOutput
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput, SeasonsListOutput
from app.shows.models import Show
from app.shows.schemas import ShowOutput, ShowsListOutput
from app.sources.models import Source
from app.sources.schemas import SourceOutput, SourcesListOutput
from app.utils import tz_datetime

router = APIRouter(
    prefix="/admin-media",
    tags=["admin-media"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/plugins")
def list_all_plugins(session: SessionDep) -> PluginsListOutput:
    """List all plugins across all users."""
    plugins = session.exec(select(Plugin)).all()
    data = [PluginOutput.model_validate(plugin) for plugin in plugins]
    return PluginsListOutput(data=data)


@router.get("/plugins/{plugin_id}/sources")
def list_plugin_sources(
    session: SessionDep,
    plugin_id: Annotated[uuid.UUID, Path()],
) -> SourcesListOutput:
    """List all sources for a plugin."""
    sources = session.exec(
        select(Source).where(Source.plugin_id == plugin_id),
    ).all()
    data = [SourceOutput.model_validate(source) for source in sources]
    return SourcesListOutput(data=data)


@router.get("/sources/{source_id}/shows")
def list_source_shows(
    session: SessionDep,
    source_id: Annotated[uuid.UUID, Path()],
) -> ShowsListOutput:
    """List all shows for a source."""
    shows = session.exec(
        select(Show).where(Show.source_id == source_id),
    ).all()
    data = [ShowOutput.model_validate(show) for show in shows]
    return ShowsListOutput(data=data)


@router.get("/shows/{show_id}/seasons")
def list_show_seasons(
    session: SessionDep,
    show_id: Annotated[uuid.UUID, Path()],
) -> SeasonsListOutput:
    """List all seasons for a show."""
    seasons = session.exec(
        select(Season).where(Season.show_id == show_id),
    ).all()
    data = [SeasonOutput.model_validate(season) for season in seasons]
    return SeasonsListOutput(data=data)


@router.get("/seasons/{season_id}/episodes")
def list_season_episodes(
    session: SessionDep,
    season_id: Annotated[uuid.UUID, Path()],
) -> EpisodesListOutput:
    """List all episodes for a season."""
    episodes = session.exec(
        select(Episode).where(Episode.season_id == season_id),
    ).all()
    data = [EpisodeOutput.model_validate(episode) for episode in episodes]
    return EpisodesListOutput(data=data)


@router.post("/plugins/{plugin_id}/trigger-update")
def trigger_plugin_update(
    session: SessionDep,
    plugin_id: Annotated[uuid.UUID, Path()],
) -> Message:
    """Set update_at to now on a plugin."""
    plugin = session.get_one(Plugin, plugin_id)
    plugin.update_at = tz_datetime.now()
    session.commit()
    return Message(message="Update triggered")


@router.post("/sources/{source_id}/trigger-update")
def trigger_source_update(
    session: SessionDep,
    source_id: Annotated[uuid.UUID, Path()],
) -> Message:
    """Set update_at to now on a source."""
    source = session.get_one(Source, source_id)
    source.update_at = tz_datetime.now()
    session.commit()
    return Message(message="Update triggered")


@router.post("/shows/{show_id}/trigger-update")
def trigger_show_update(
    session: SessionDep,
    show_id: Annotated[uuid.UUID, Path()],
) -> Message:
    """Set update_at to now on a show."""
    show = session.get_one(Show, show_id)
    show.update_at = tz_datetime.now()
    session.commit()
    return Message(message="Update triggered")


@router.post("/seasons/{season_id}/trigger-update")
def trigger_season_update(
    session: SessionDep,
    season_id: Annotated[uuid.UUID, Path()],
) -> Message:
    """Set update_at to now on a season."""
    season = session.get_one(Season, season_id)
    season.update_at = tz_datetime.now()
    session.commit()
    return Message(message="Update triggered")


@router.post("/episodes/{episode_id}/trigger-update")
def trigger_episode_update(
    session: SessionDep,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Message:
    """Set update_at to now on an episode."""
    episode = session.get_one(Episode, episode_id)
    episode.update_at = tz_datetime.now()
    session.commit()
    return Message(message="Update triggered")
