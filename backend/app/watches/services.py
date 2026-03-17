# TODO: Validate
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlmodel import Session, col, or_, select

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.models import Plugin
from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins
from app.plugins.schemas import PluginOutput
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowOutput
from app.sources.models import Source
from app.sources.schemas import SourceOutput
from app.watches.models import Watch
from app.watches.schemas import (
    WatchesListOutput,
    WatchItem,
)

if TYPE_CHECKING:
    from app.plugins.plugins.utils.abstract_plugin import AbstractPlugin


def _episode_watch_select_statement(
    session: Session,
    user_id: uuid.UUID,
) -> Sequence[Watch]:
    # TODO: Consider changing this to joinedload if performance changes
    statement = (
        select(Watch).join(Episode).join(Season).join(Show).join(Source).join(Plugin)
    )
    statement = statement.where(Watch.user_id == user_id)
    statement = statement.where(
        or_(col(Plugin.public).is_(True), col(Plugin.user_id) == user_id),
    )
    return session.exec(statement).all()


def get_watched_episodes(
    session: Session,
    user_id: uuid.UUID,
) -> WatchesListOutput:
    episode_watches = _episode_watch_select_statement(session, user_id)
    return _format_watched_episodes_data(episode_watches)


def _format_watched_episodes_data(
    episode_watches: Sequence[Watch],
) -> WatchesListOutput:
    episodes_dict: dict[uuid.UUID, EpisodeOutput] = {}
    seasons_dict: dict[uuid.UUID, SeasonOutput] = {}
    shows_dict: dict[uuid.UUID, ShowOutput] = {}
    sources_dict: dict[uuid.UUID, SourceOutput] = {}
    plugins_dict: dict[uuid.UUID, PluginOutput] = {}
    watches: list[WatchItem] = []

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
            WatchItem(
                id=episode_watch.id,
                episode_id=episode.id,
                watch_date=episode_watch.watch_date,
                verified=episode_watch.verified,
            ),
        )

    return WatchesListOutput(
        watches=watches,
        episodes=episodes_dict,
        seasons=seasons_dict,
        shows=shows_dict,
        sources=sources_dict,
        plugins=plugins_dict,
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


def get_installed_plugin(plugin_key: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_key."""
    for plugin_cls in get_importable_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            return plugin_cls
    return None
