from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlmodel import select

from app.admin_media.service import force_update
from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.episodes.dependencies import ReadableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.dependencies import ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.dependencies import ReadableShow
from app.shows.models import Show
from app.shows.schemas import ShowOutput
from app.sources.dependencies import ReadableSource
from app.sources.models import Source
from app.sources.schemas import SourceOutput
from app.users.service import get_or_create_plugin_user

router = APIRouter(
    prefix="/admin-media",
    tags=["admin-media"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/plugins", response_model=list[PluginOutput])
def list_all_plugins(session: SessionDep) -> Sequence[Plugin]:
    """List all plugins owned by the plugin user."""
    plugin_user = get_or_create_plugin_user(session=session)
    plugin_select = select(Plugin).where(Plugin.user_id == plugin_user.id)
    return session.exec(plugin_select).all()


@router.get("/plugins/{plugin_id}/sources", response_model=list[SourceOutput])  # noqa: FAST003 - Used by ReadablePlugin
def list_plugin_sources(plugin: ReadablePlugin) -> list[Source]:
    """List all sources for a plugin."""
    return list(plugin.sources)


@router.get("/sources/{source_id}/shows", response_model=list[ShowOutput])  # noqa: FAST003 - Used by ReadableSource
def list_source_shows(source: ReadableSource) -> list[Show]:
    """List all shows for a source."""
    return list(source.shows)


@router.get("/shows/{show_id}/seasons", response_model=list[SeasonOutput])  # noqa: FAST003 - Used by ReadableShow
def list_show_seasons(show: ReadableShow) -> list[Season]:
    """List all seasons for a show."""
    return list(show.seasons)


@router.get("/seasons/{season_id}/episodes", response_model=list[EpisodeOutput])  # noqa: FAST003 - Used by ReadableSeason
def list_season_episodes(season: ReadableSeason) -> list[Episode]:
    """List all episodes for a season."""
    return list(season.episodes)


@router.post("/plugins/{plugin_id}/force-update")  # noqa: FAST003 - Used by ReadablePlugin
def force_plugin_update(session: SessionDep, plugin: ReadablePlugin) -> Message:
    """Force update a plugin by setting its update_at value to now."""
    return force_update(session, plugin)


@router.post("/sources/{source_id}/force-update")  # noqa: FAST003 - Used by ReadableSource
def force_source_update(session: SessionDep, source: ReadableSource) -> Message:
    """Force update a source by setting its update_at value to now."""
    return force_update(session, source)


@router.post("/shows/{show_id}/force-update")  # noqa: FAST003 - Used by ReadableShow
def force_show_update(session: SessionDep, show: ReadableShow) -> Message:
    """Force update a show by setting its update_at value to now."""
    return force_update(session, show)


@router.post("/seasons/{season_id}/force-update")  # noqa: FAST003 - Used by ReadableSeason
def force_season_update(session: SessionDep, season: ReadableSeason) -> Message:
    """Force update a season by setting its update_at value to now."""
    return force_update(session, season)


@router.post("/episodes/{episode_id}/force-update")  # noqa: FAST003 - Used by ReadableEpisode
def force_episode_update(session: SessionDep, episode: ReadableEpisode) -> Message:
    """Force update an episode by setting its update_at value to now."""
    return force_update(session, episode)
