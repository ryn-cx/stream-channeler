# TODO: Validate

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile, status
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.constants import MAX_ENTRIES_PER_PAGE
from app.media.dependencies import ExistingEpisode, ExistingEpisodeWatch
from app.media.models import Episode, EpisodeWatch, Plugin, Season, Show, Source
from app.media.schemas import (
    EpisodeInput,
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
    EpisodeWatchPatchInput,
    EpisodeWatchPostInput,
    PluginInput,
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
    PluginsListOutput,
    SeasonInput,
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
    ShowInput,
    ShowOutput,
    ShowPatchInput,
    ShowPostInput,
    ShowsListOutput,
    SingleEpisodeWatchOutput,
    SourceInput,
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
    WatchedEpisodesOutput,
    WatchImportInput,
    WatchImportPluginsOutput,
    WatchImportResult,
)
from app.media.services import (
    get_importable_plugins,
    get_installed_plugin,
    get_user_episode,
    get_user_plugin,
    get_user_season,
    get_user_show,
    get_user_source,
    save_episode_watch,
)
from app.media.services import get_watched_episodes as get_watched_episodes_service
from app.models import Message

router = APIRouter()
episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])
plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])
sources_router = APIRouter(prefix="/sources", tags=["sources"])
shows_router = APIRouter(prefix="/shows", tags=["shows"])
seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])


# region List


@plugins_router.get("/")
def get_plugins_from_user(
    session: SessionDep,
    current_user: CurrentUser,
) -> PluginsListOutput:
    """List all plugins owned by the current user."""
    statement = select(Plugin).where(Plugin.user_id == current_user.id)
    plugins = session.exec(statement).all()
    return PluginsListOutput(data=plugins, count=len(plugins))  # type: ignore[arg-type]


@plugins_router.get("/{plugin_key}/sources", response_model=SourcesListOutput)
def get_sources_from_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_key: str,
) -> SourcesListOutput:
    """List all sources for a plugin owned by the current user."""
    plugin = get_user_plugin(session, current_user, plugin_key)
    statement = select(Source).where(Source.plugin_id == plugin.id)
    sources = session.exec(statement).all()
    return SourcesListOutput(data=sources, count=len(sources))  # type: ignore[arg-type]


@sources_router.get("/{source_id}/shows", response_model=ShowsListOutput)
def get_shows_from_source(
    session: SessionDep,
    current_user: CurrentUser,
    source_id: uuid.UUID,
) -> ShowsListOutput:
    """List all shows for a source."""
    source = get_user_source(session, current_user, source_id)
    statement = select(Show).where(Show.source_id == source.id)
    shows = session.exec(statement).all()
    return ShowsListOutput(data=shows, count=len(shows))  # type: ignore[arg-type]


@shows_router.get("/{show_id}/seasons", response_model=SeasonsListOutput)
def get_seasons_from_show(
    session: SessionDep,
    current_user: CurrentUser,
    show_id: uuid.UUID,
) -> SeasonsListOutput:
    """List all seasons for a show."""
    show = get_user_show(session, current_user, show_id)
    statement = select(Season).where(Season.show_id == show.id)
    seasons = session.exec(statement).all()
    return SeasonsListOutput(data=seasons, count=len(seasons))  # type: ignore[arg-type]


@seasons_router.get("/{season_id}/episodes", response_model=EpisodesListOutput)
def get_episodes_from_season(
    session: SessionDep,
    current_user: CurrentUser,
    season_id: uuid.UUID,
) -> EpisodesListOutput:
    """List all episodes for a season."""
    season = get_user_season(session, current_user, season_id)
    statement = select(Episode).where(Episode.season_id == season.id)
    episodes = session.exec(statement).all()
    return EpisodesListOutput(data=episodes, count=len(episodes))  # type: ignore[arg-type]


# endregion

# region Create


@plugins_router.post("/", response_model=PluginOutput)
def create_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    body: PluginPostInput,
) -> Plugin:
    """Create a plugin owned by the current user."""
    plugin = PluginInput(
        key=str(uuid.uuid4()),
        user_id=current_user.id,
        **body.model_dump(),
    ).upsert(session, None)
    session.commit()
    return plugin


@sources_router.post("/", response_model=SourceOutput)
def create_source(
    session: SessionDep,
    current_user: CurrentUser,
    body: SourcePostInput,
) -> Source:
    """Create a source for a plugin."""
    plugin = get_user_plugin(session, current_user, body.plugin_key)
    existing = session.exec(
        select(Source).where(Source.plugin_id == plugin.id, Source.key == body.key),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source with this key already exists",
        )
    source = SourceInput(
        **body.model_dump(exclude={"plugin_key"}),
    ).upsert(plugin, None)
    session.commit()
    return source


@shows_router.post("/", response_model=ShowOutput)
def create_show(
    session: SessionDep,
    current_user: CurrentUser,
    body: ShowPostInput,
) -> Show:
    """Create a show for a source."""
    source = get_user_source(session, current_user, body.source_id)
    existing = session.exec(
        select(Show).where(Show.source_id == source.id, Show.key == body.key),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Show with this key already exists",
        )
    show = ShowInput(
        **body.model_dump(exclude={"source_id"}),
    ).upsert(source, None)
    session.commit()
    return show


@seasons_router.post("/", response_model=SeasonOutput)
def create_season(
    session: SessionDep,
    current_user: CurrentUser,
    body: SeasonPostInput,
) -> Season:
    """Create a season for a show."""
    show = get_user_show(session, current_user, body.show_id)
    existing = session.exec(
        select(Season).where(Season.show_id == show.id, Season.key == body.key),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Season with this key already exists",
        )
    season = SeasonInput(
        **body.model_dump(exclude={"show_id"}),
    ).upsert(show, None)
    session.commit()
    return season


@episodes_router.post("/", response_model=EpisodeOutput)
def create_episode(
    session: SessionDep,
    current_user: CurrentUser,
    body: EpisodePostInput,
) -> Episode:
    """Create an episode for a season."""
    season = get_user_season(session, current_user, body.season_id)
    existing = session.exec(
        select(Episode).where(
            Episode.season_id == season.id,
            Episode.key == body.key,
        ),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Episode with this key already exists",
        )
    episode = EpisodeInput(
        **body.model_dump(exclude={"season_id"}),
    ).upsert(season, None)
    session.commit()
    return episode


# endregion

# region Update


@plugins_router.patch("/{plugin_key}", response_model=PluginOutput)
def update_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_key: str,
    body: PluginPatchInput,
) -> Plugin:
    """Update a plugin owned by the current user."""
    plugin = get_user_plugin(session, current_user, plugin_key)
    plugin.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(plugin)
    return plugin


@sources_router.patch("/{source_id}", response_model=SourceOutput)
def update_source(
    session: SessionDep,
    current_user: CurrentUser,
    source_id: uuid.UUID,
    body: SourcePatchInput,
) -> Source:
    """Update a source by its id."""
    source = get_user_source(session, current_user, source_id)
    source.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(source)
    return source


@shows_router.patch("/{show_id}", response_model=ShowOutput)
def update_show(
    session: SessionDep,
    current_user: CurrentUser,
    show_id: uuid.UUID,
    body: ShowPatchInput,
) -> Show:
    """Update a show by its id."""
    show = get_user_show(session, current_user, show_id)
    show.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(show)
    return show


@seasons_router.patch("/{season_id}", response_model=SeasonOutput)
def update_season(
    session: SessionDep,
    current_user: CurrentUser,
    season_id: uuid.UUID,
    body: SeasonPatchInput,
) -> Season:
    """Update a season by its id."""
    season = get_user_season(session, current_user, season_id)
    season.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(season)
    return season


@episodes_router.patch("/{episode_id}", response_model=EpisodeOutput)
def update_episode(
    session: SessionDep,
    current_user: CurrentUser,
    episode_id: uuid.UUID,
    body: EpisodePatchInput,
) -> Episode:
    """Update an episode by its id."""
    episode = get_user_episode(session, current_user, episode_id)
    episode.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(episode)
    return episode


# endregion

# region Delete


@plugins_router.delete("/{plugin_key}")
def delete_user_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_key: str,
) -> dict[str, str]:
    """Delete a plugin owned by the current user."""
    plugin = get_user_plugin(session, current_user, plugin_key)
    session.delete(plugin)
    session.commit()
    return {"message": "Plugin deleted successfully"}


@sources_router.delete("/{source_id}")
def delete_source(
    session: SessionDep,
    current_user: CurrentUser,
    source_id: uuid.UUID,
) -> dict[str, str]:
    """Delete a source by its id."""
    source = get_user_source(session, current_user, source_id)
    session.delete(source)
    session.commit()
    return {"message": "Source deleted successfully"}


@shows_router.delete("/{show_id}")
def delete_show(
    session: SessionDep,
    current_user: CurrentUser,
    show_id: uuid.UUID,
) -> dict[str, str]:
    """Delete a show by its id."""
    show = get_user_show(session, current_user, show_id)
    session.delete(show)
    session.commit()
    return {"message": "Show deleted successfully"}


@seasons_router.delete("/{season_id}")
def delete_season(
    session: SessionDep,
    current_user: CurrentUser,
    season_id: uuid.UUID,
) -> dict[str, str]:
    """Delete a season by its id."""
    season = get_user_season(session, current_user, season_id)
    session.delete(season)
    session.commit()
    return {"message": "Season deleted successfully"}


@episodes_router.delete("/{episode_id}")
def delete_episode(
    session: SessionDep,
    current_user: CurrentUser,
    episode_id: uuid.UUID,
) -> dict[str, str]:
    """Delete an episode by its id."""
    episode = get_user_episode(session, current_user, episode_id)
    session.delete(episode)
    session.commit()
    return {"message": "Episode deleted successfully"}


# endregion

# region Episode Watches


@episodes_router.post("/watches")
def post_watched_episode(
    session: SessionDep,
    current_user: CurrentUser,
    watch_input: EpisodeWatchPostInput,
    episode: ExistingEpisode,
) -> SingleEpisodeWatchOutput:
    """Create a new episode watch entry."""
    episode_watch = EpisodeWatch(
        user_id=current_user.id,
        episode_id=watch_input.episode_id,
    )
    session.add(episode_watch)

    return save_episode_watch(
        session,
        episode_watch,
        episode,
        watch_input,
    )


# FAST003 - Parameter is used by EpisodeWatchDep
@episodes_router.patch("/watches/{episode_watch_id}")  # noqa: FAST003
def patch_watched_episode(
    session: SessionDep,
    episode_watch: ExistingEpisodeWatch,
    watch_input: EpisodeWatchPatchInput,
) -> SingleEpisodeWatchOutput:
    """Update an existing episode watch entry."""
    return save_episode_watch(
        session,
        episode_watch,
        episode_watch.episode,
        watch_input,
    )


# FAST003 - Parameter is used by EpisodeWatchDep
@episodes_router.delete("/watches/{episode_watch_id}")  # noqa: FAST003
def delete_watched_episode(
    session: SessionDep,
    episode_watch: ExistingEpisodeWatch,
) -> Message:
    """Delete an existing episode watch entry."""
    session.delete(episode_watch)
    session.commit()
    return Message(message="Episode watch deleted")


@episodes_router.get("/watches")
def get_watched_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = MAX_ENTRIES_PER_PAGE,
) -> WatchedEpisodesOutput:
    """Get multiple watched episode entries."""
    return get_watched_episodes_service(session, current_user.id, skip, limit)


@episodes_router.get("/watches/import/plugins")
def list_importable_plugins(_current_user: CurrentUser) -> WatchImportPluginsOutput:
    """List all plugins that support importing watch history."""
    return WatchImportPluginsOutput(
        plugins=[
            plugin.import_watch_history_info() for plugin in get_importable_plugins()
        ],
    )


@episodes_router.post("/watches/import")
def import_watch_history(
    file: UploadFile,
    params: Annotated[WatchImportInput, Query()],
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchImportResult:
    """Import watch history from an uploaded file for a specific plugin."""
    if not (plugin := get_installed_plugin(params.plugin_id)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Plugin '{params.plugin_id}' does not support watch import.",
        )

    content_bytes = file.file.read()
    content = content_bytes.decode("utf-8")

    plugin_instance = plugin(db=session)
    result = plugin_instance.import_watch_history(
        content=content,
        user=current_user,
        new_only=params.new_only,
        verified=params.verified,
    )
    session.commit()
    return result


# endregion

router.include_router(episodes_router)
router.include_router(plugins_router)
router.include_router(sources_router)
router.include_router(shows_router)
router.include_router(seasons_router)
