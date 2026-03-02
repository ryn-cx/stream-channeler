# TODO: Validate

import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, func, select

from app.media.models import Episode, EpisodeWatch, Plugin, Season, Show, Source
from app.media.schemas import (
    EpisodeOutput,
    EpisodeWatchItem,
    EpisodeWatchPatchInput,
    EpisodeWatchPostInput,
    PluginOutput,
    SeasonOutput,
    ShowOutput,
    SingleEpisodeWatchOutput,
    SourceOutput,
    WatchedEpisodesOutput,
)
from app.plugins.utils.manage_plugins import import_plugins, plugins
from app.users.models import User

if TYPE_CHECKING:
    from app.plugins.utils.abstract_plugin import AbstractPlugin


def get_user_plugin(
    session: Session,
    current_user: User,
    plugin_key: str,
) -> Plugin:
    """Get a plugin owned by the current user or raise 404."""
    plugin = Plugin.get(session, plugin_key)
    if not plugin or plugin.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin not found",
        )
    return plugin


def get_user_source(
    session: Session,
    current_user: User,
    source_id: uuid.UUID,
) -> Source:
    """Look up a source by its UUID id and verify user ownership."""
    statement = (
        select(Source)
        .where(Source.id == source_id)
        .options(selectinload(Source.plugin))  # type: ignore[arg-type]
    )
    source = session.exec(statement).first()
    if not source or source.plugin.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )
    return source


def get_user_show(
    session: Session,
    current_user: User,
    show_id: uuid.UUID,
) -> Show:
    """Look up a show by its UUID id and verify user ownership."""
    statement = (
        select(Show)
        .where(Show.id == show_id)
        .options(
            selectinload(Show.source).selectinload(Source.plugin),  # type: ignore[arg-type]
        )
    )
    show = session.exec(statement).first()
    if not show or show.source.plugin.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Show not found",
        )
    return show


def get_user_season(
    session: Session,
    current_user: User,
    season_id: uuid.UUID,
) -> Season:
    """Look up a season by its UUID id and verify user ownership."""
    statement = (
        select(Season)
        .where(Season.id == season_id)
        .options(
            selectinload(Season.show)  # type: ignore[arg-type]
            .selectinload(Show.source)  # type: ignore[arg-type]
            .selectinload(Source.plugin),  # type: ignore[arg-type]
        )
    )
    season = session.exec(statement).first()
    if not season or season.show.source.plugin.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Season not found",
        )
    return season


def get_user_episode(
    session: Session,
    current_user: User,
    episode_id: uuid.UUID,
) -> Episode:
    """Look up an episode by its UUID id and verify user ownership."""
    statement = (
        select(Episode)
        .where(Episode.id == episode_id)
        .options(
            selectinload(Episode.season)  # type: ignore[arg-type]
            .selectinload(Season.show)  # type: ignore[arg-type]
            .selectinload(Show.source)  # type: ignore[arg-type]
            .selectinload(Source.plugin),  # type: ignore[arg-type]
        )
    )
    episode = session.exec(statement).first()
    if not episode or episode.season.show.source.plugin.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Episode not found",
        )
    return episode


def _episode_watch_count_statement(session: Session, user_id: uuid.UUID) -> int:
    # TODO: Consider changing this to joinedload if performance changes
    statement = (
        select(func.count())
        .select_from(EpisodeWatch)
        .join(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
    )
    statement = statement.where(EpisodeWatch.user_id == user_id)
    return session.exec(statement).one()


def _episode_watch_select_statement(
    session: Session,
    user_id: uuid.UUID,
    skip: int,
    limit: int,
) -> Sequence[EpisodeWatch]:
    # TODO: Consider changing this to joinedload if performance changes
    statement = (
        select(EpisodeWatch)
        .join(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
        .order_by(col(EpisodeWatch.verified).asc(), col(EpisodeWatch.watch_date).desc())
        .offset(skip)
        .limit(limit)
    )
    statement = statement.where(EpisodeWatch.user_id == user_id)
    return session.exec(statement).all()


def get_watched_episodes(
    session: Session,
    user_id: uuid.UUID,
    skip: int,
    limit: int,
) -> WatchedEpisodesOutput:
    count = _episode_watch_count_statement(session, user_id)
    episode_watches = _episode_watch_select_statement(session, user_id, skip, limit)
    return _format_watched_episodes_data(episode_watches, count)


def _format_watched_episodes_data(
    episode_watches: Sequence[EpisodeWatch],
    count: int,
) -> WatchedEpisodesOutput:
    episodes_dict: dict[uuid.UUID, EpisodeOutput] = {}
    seasons_dict: dict[uuid.UUID, SeasonOutput] = {}
    shows_dict: dict[uuid.UUID, ShowOutput] = {}
    sources_dict: dict[uuid.UUID, SourceOutput] = {}
    plugins_dict: dict[uuid.UUID, PluginOutput] = {}
    watches: list[EpisodeWatchItem] = []

    for episode_watch in episode_watches:
        episode = episode_watch.episode
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        if episode.id not in episodes_dict:
            episodes_dict[episode.id] = EpisodeOutput.model_validate(episode)
        if season.id not in seasons_dict:
            seasons_dict[season.id] = SeasonOutput.model_validate(season)
        if show.id not in shows_dict:
            shows_dict[show.id] = ShowOutput.model_validate(show)
        if source.id not in sources_dict:
            sources_dict[source.id] = SourceOutput.model_validate(source)
        if plugin.id not in plugins_dict:
            plugins_dict[plugin.id] = PluginOutput.model_validate(plugin)

        watches.append(
            EpisodeWatchItem(
                id=episode_watch.id,
                episode_id=episode.id,
                watch_date=episode_watch.watch_date,
                verified=episode_watch.verified,
            ),
        )

    return WatchedEpisodesOutput(
        watches=watches,
        episodes=episodes_dict,
        seasons=seasons_dict,
        shows=shows_dict,
        sources=sources_dict,
        plugins=plugins_dict,
        count=count,
    )


def save_episode_watch(
    session: Session,
    episode_watch: EpisodeWatch,
    episode: Episode,
    watch_input: EpisodeWatchPatchInput | EpisodeWatchPostInput,
) -> SingleEpisodeWatchOutput:
    if watch_input.watch_date is not None:
        episode_watch.watch_date = watch_input.watch_date
    if watch_input.verified is not None:
        episode_watch.verified = watch_input.verified
    session.commit()

    return SingleEpisodeWatchOutput(
        id=episode_watch.id,
        watch_date=episode_watch.watch_date,
        verified=episode_watch.verified,
        episode=EpisodeOutput.model_validate(episode),
        season=SeasonOutput.model_validate(episode.season),
        show=ShowOutput.model_validate(episode.season.show),
        source=SourceOutput.model_validate(episode.season.show.source),
        plugin=PluginOutput.model_validate(episode.season.show.source.plugin),
    )


def get_importable_plugins() -> list[type[AbstractPlugin]]:
    """Return all plugin classes that support watch import."""
    import_plugins()
    result: list[type[AbstractPlugin]] = []
    for plugin_cls in plugins:
        try:
            plugin_cls.import_watch_history_info()
            result.append(plugin_cls)
        except NotImplementedError:
            continue
    return result


def get_installed_plugin(plugin_id: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_id."""
    for plugin_cls in get_importable_plugins():
        if plugin_cls.plugin_id() == plugin_id:
            return plugin_cls
    return None
