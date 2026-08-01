# TODO: Validate
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.media.service import delete_record
from app.models import Visibility
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import Message, ReadOptions
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.service import get_read_results
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.users.models import User
from app.users.service import get_or_create_plugin_user
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchesListOutput,
    WatchItem,
    WatchOutput,
    WatchUpdate,
)
from plugins.utils.manage_plugins import import_plugins, plugins

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import AbstractPlugin

# The episode a watch points at; reads still group watches by that episode's
# `episode_identifier` so a watch counts across every source sharing it.
WatchedEpisode = aliased(Episode)


def _visible_plugin_condition(user_id: uuid.UUID):  # noqa: ANN202
    return or_(
        col(Plugin.visibility).in_((Visibility.public, Visibility.unlisted)),
        col(Plugin.user_id) == user_id,
    )


def _watched_identifiers_subquery(user_id: uuid.UUID):  # noqa: ANN202
    return (
        select(col(WatchedEpisode.episode_identifier))
        .join(Watch, col(Watch.episode_id) == col(WatchedEpisode.id))
        .where(Watch.user_id == user_id)
    )


def _representative_episode_subquery(user_id: uuid.UUID, identifiers):  # noqa: ANN001, ANN202
    """One representative visible episode per `episode_identifier`.

    A watch keys on `episode_identifier`, which can resolve to an episode in every
    source that shares it. This picks a single visible episode per identifier so a
    watch can be joined to concrete media for display and visibility filtering.
    Restricted to `identifiers` so it only resolves the identifiers actually in play
    instead of the whole episode catalog.
    """
    return (
        select(
            col(Episode.episode_identifier).label("episode_identifier"),
            col(Episode.id).label("episode_id"),
        )
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(Episode.deleted_at).is_(None))
        .where(_visible_plugin_condition(user_id))
        .where(col(Episode.episode_identifier).in_(identifiers))
        .distinct(col(Episode.episode_identifier))
        .order_by(col(Episode.episode_identifier), col(Episode.id))
        .subquery()
    )


def _episode_watch_base_statement(user_id: uuid.UUID) -> SelectOfScalar[Watch]:
    representative = _representative_episode_subquery(
        user_id,
        _watched_identifiers_subquery(user_id),
    )
    return (
        select(Watch)
        .join(WatchedEpisode, col(Watch.episode_id) == col(WatchedEpisode.id))
        .join(
            representative,
            representative.c.episode_identifier
            == col(WatchedEpisode.episode_identifier),
        )
        .join(Episode, col(Episode.id) == representative.c.episode_id)
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(Watch.user_id == user_id)
    )


def get_watched_episodes(
    session: Session,
    user: User,
    read_options: ReadOptions,
) -> WatchesListOutput:
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        _episode_watch_base_statement(user.id),
        schema=WatchOutput,
        default_sort=Watch.watch_date,
        tiebreaker=Watch.id,
        params=read_options,
        current_user=user,
        extra_columns={
            "plugin": col(Plugin.name),
            "source": col(Source.name),
            "show": col(Show.name),
            "season": col(Season.name),
            "episode": col(Episode.name),
        },
    )
    output = _format_watched_episodes_data(session, user.id, rows)
    output.total_count = total_count
    output.filtered_count = filtered_count
    output.is_server_side = is_server_side
    return output


def _representative_episodes_by_identifier(
    session: Session,
    user_id: uuid.UUID,
    identifiers: set[str],
) -> dict[str, Episode]:
    """Load the representative visible `Episode` for each `episode_identifier`."""
    if not identifiers:
        return {}
    representative = _representative_episode_subquery(user_id, identifiers)
    episodes = session.exec(
        select(Episode).join(
            representative,
            col(Episode.id) == representative.c.episode_id,
        ),
    ).all()
    return {episode.episode_identifier: episode for episode in episodes}


def _format_watched_episodes_data(
    session: Session,
    user_id: uuid.UUID,
    episode_watches: Sequence[Watch],
) -> WatchesListOutput:
    episodes_dict: dict[str, EpisodeOutput] = {}
    seasons_dict: dict[uuid.UUID, SeasonOutput] = {}
    shows_dict: dict[uuid.UUID, ShowPublic] = {}
    sources_dict: dict[uuid.UUID, SourcePublic] = {}
    plugins_dict: dict[uuid.UUID, PluginOutput] = {}
    watches: list[WatchItem] = []

    episode_by_identifier = _representative_episodes_by_identifier(
        session,
        user_id,
        {watch.episode.episode_identifier for watch in episode_watches},
    )

    for episode_watch in episode_watches:
        episode = episode_by_identifier.get(
            episode_watch.episode.episode_identifier,
        )
        if episode is None:
            continue
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        if episode.episode_identifier not in episodes_dict:
            episodes_dict[episode.episode_identifier] = EpisodeOutput.model_validate(
                episode,
            )
        if season.id not in seasons_dict:
            seasons_dict[season.id] = SeasonOutput.model_validate(season)
        if show.id not in shows_dict:
            shows_dict[show.id] = ShowPublic.model_validate(show)
        if source.id not in sources_dict:
            sources_dict[source.id] = SourcePublic.model_validate(source)
        if plugin.id not in plugins_dict:
            plugins_dict[plugin.id] = PluginOutput.model_validate(plugin)

        watches.append(
            WatchItem(
                id=episode_watch.id,
                episode_id=episode_watch.episode_id,
                episode_identifier=episode_watch.episode.episode_identifier,
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


def create_watches(
    session: Session,
    user_id: uuid.UUID,
    episode: Episode,
    watch_input: WatchCreate,
) -> list[WatchOutput]:
    """Create a watch for the episode's `episode_identifier`.

    Raises 409 Conflict if the identifier already has an unverified watch.
    """
    existing_unverified = session.exec(
        select(Watch)
        .join(WatchedEpisode, col(Watch.episode_id) == col(WatchedEpisode.id))
        .where(
            Watch.user_id == user_id,
            col(WatchedEpisode.episode_identifier) == episode.episode_identifier,
            col(Watch.verified) == False,  # noqa: E712 - TODO: SQLAlchemy comparison requires == False
        ),
    ).first()
    if existing_unverified:
        raise HTTPException(
            status_code=409,
            detail="Episode already has an unverified watch. Verify or delete it first.",
        )

    watch = Watch.model_validate(
        watch_input,
        update={
            "episode_id": episode.id,
            "user_id": user_id,
        },
    )
    session.add(watch)
    session.commit()
    session.refresh(watch)
    return [WatchOutput.model_validate(watch)]


def update_watches(
    session: Session,
    input_watch: Watch,
    watch_input: WatchUpdate,
) -> list[WatchOutput]:
    """Update a watch."""
    watch_input.update(session, input_watch)
    return [WatchOutput.model_validate(input_watch)]


def delete_watches(session: Session, input_watch: Watch) -> Message:
    """Delete a watch."""
    delete_record(session, input_watch)
    return Message(message="Watch deleted successfully")


def get_plugins_with_import_watch_history(
    session: Session,
) -> list[type[AbstractPlugin]]:
    """Return all plugin classes that support watch import.

    Only includes plugins that are owned by the official plugin user.
    """
    import_plugins()
    plugin_user = get_or_create_plugin_user(session=session)

    return [
        plugin_cls
        for plugin_cls in plugins
        if plugin_cls.implements("import_watch_history")
        and Plugin.get(session, plugin_user, plugin_cls.plugin_key())
    ]


def get_installed_plugin(plugin_key: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_key."""
    import_plugins()
    for plugin_cls in plugins:
        if plugin_cls.plugin_key() == plugin_key:
            return plugin_cls
    return None
