# TODO: Validate
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
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


def _episode_watch_base_statement(user_id: uuid.UUID) -> SelectOfScalar[Watch]:
    return (
        select(Watch)
        .join(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(Watch.user_id == user_id)
        .where(
            or_(
                col(Plugin.visibility).in_((Visibility.public, Visibility.unlisted)),
                col(Plugin.user_id) == user_id,
            ),
        )
    )


def _episode_watch_select_statement(
    session: Session,
    user_id: uuid.UUID,
) -> Sequence[Watch]:
    return session.exec(_episode_watch_base_statement(user_id)).all()


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
    output = _format_watched_episodes_data(rows)
    output.total_count = total_count
    output.filtered_count = filtered_count
    output.is_server_side = is_server_side
    return output


def _format_watched_episodes_data(
    episode_watches: Sequence[Watch],
) -> WatchesListOutput:
    episodes_dict: dict[uuid.UUID, EpisodeOutput] = {}
    seasons_dict: dict[uuid.UUID, SeasonOutput] = {}
    shows_dict: dict[uuid.UUID, ShowPublic] = {}
    sources_dict: dict[uuid.UUID, SourcePublic] = {}
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
            shows_dict[show.id] = ShowPublic.model_validate(show)
        if source.id not in sources_dict:
            sources_dict[source.id] = SourcePublic.model_validate(source)
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


def create_watches(
    session: Session,
    user_id: uuid.UUID,
    episode: Episode,
    watch_input: WatchCreate,
) -> list[WatchOutput]:
    """Create watches for all episodes with the same key in the same plugin.

    Raises 409 Conflict if any matching episode already has an unverified watch.
    """
    all_episodes = get_matching_episodes(session, episode)
    all_episode_ids = [episode.id for episode in all_episodes]
    existing_unverified = session.exec(
        select(Watch).where(
            Watch.user_id == user_id,
            col(Watch.episode_id).in_(all_episode_ids),
            col(Watch.verified) == False,  # noqa: E712 - TODO: SQLAlchemy comparison requires == False
        ),
    ).first()
    if existing_unverified:
        raise HTTPException(
            status_code=409,
            detail="Episode already has an unverified watch. Verify or delete it first.",
        )

    created: list[Watch] = []
    for target_episode in all_episodes:
        watch = Watch.model_validate(
            watch_input,
            update={"episode_id": target_episode.id, "user_id": user_id},
        )
        session.add(watch)
        created.append(watch)
    session.commit()
    for watch in created:
        session.refresh(watch)
    return [WatchOutput.model_validate(watch) for watch in created]


def get_matching_episodes(
    session: Session,
    episode: Episode,
) -> list[Episode]:
    """Find all episodes with the same key in the same plugin."""
    plugin_id = episode.season.show.source.plugin_id
    return list(
        session.exec(
            select(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .where(Source.plugin_id == plugin_id)
            .where(Episode.key == episode.key),
        ).all(),
    )


def get_matching_watches(session: Session, watch: Watch) -> list[Watch]:
    """Get all watches with the same date, key, and plugin."""
    episode_ids = [ep.id for ep in get_matching_episodes(session, watch.episode)]
    return list(
        session.exec(
            select(Watch).where(
                Watch.user_id == watch.user_id,
                col(Watch.episode_id).in_(episode_ids),
                Watch.watch_date == watch.watch_date,
            ),
        ).all(),
    )


def update_watches(
    session: Session,
    input_watch: Watch,
    watch_input: WatchUpdate,
) -> list[WatchOutput]:
    """Update a watch and all matching watches."""
    all_watches = get_matching_watches(session, input_watch)
    for watch in all_watches:
        watch_input.update(session, watch)
    return [WatchOutput.model_validate(watch) for watch in all_watches]


def delete_watches(session: Session, input_watch: Watch) -> Message:
    """Delete a watch and all matching watches."""
    all_watches = get_matching_watches(session, input_watch)
    for watch in all_watches:
        delete_record(session, watch)
    if len(all_watches) > 1:
        return Message(message=f"{len(all_watches)} watches deleted successfully")
    return Message(message="Watch deleted successfully")


def sync_episode_watches(session: Session, user_id: uuid.UUID) -> Message:
    """Sync watches across episodes with the same key within the same plugin."""
    watches = _episode_watch_select_statement(session, user_id)

    grouped_watches: defaultdict[uuid.UUID, defaultdict[str, list[Watch]]] = (
        defaultdict(
            lambda: defaultdict(list),
        )
    )
    for watch in watches:
        plugin_id = watch.episode.season.show.source.plugin_id
        grouped_watches[plugin_id][watch.episode.key].append(watch)

    created = 0
    # Go through all of the watches for each plugin at once.
    for plugin_id, episode_watch_dict in grouped_watches.items():
        episodes_by_key = _get_plugin_episodes_by_key(
            session,
            plugin_id,
            list(episode_watch_dict.keys()),
        )

        existing_watch_dates = _get_existing_watch_dates(watches)

        # Loop through every episode that has a watch.
        for watched_episode_key, group_watches in episode_watch_dict.items():
            # Loop through every watch for the episode.
            for watch in group_watches:
                # Go through every episode with the same key and create the watch if
                # needed.
                for episode in episodes_by_key[watched_episode_key]:
                    # Use the watch date to determine if a watch already exists.
                    if watch.watch_date in existing_watch_dates[episode.id]:
                        continue

                    session.add(
                        Watch(
                            user_id=user_id,
                            episode_id=episode.id,
                            watch_date=watch.watch_date,
                            verified=watch.verified,
                        ),
                    )
                    existing_watch_dates[episode.id].add(watch.watch_date)
                    created += 1

    session.commit()
    return Message(message=f"Sync complete: {created} watches created")


def _get_existing_watch_dates(
    watches: Sequence[Watch],
) -> defaultdict[uuid.UUID, set[datetime]]:
    """Build a mapping of episode ID to set of watch dates."""
    existing_watch_dates: defaultdict[uuid.UUID, set[datetime]] = defaultdict(set)
    for watch in watches:
        existing_watch_dates[watch.episode_id].add(watch.watch_date)
    return existing_watch_dates


def _get_plugin_episodes_by_key(
    session: Session,
    plugin_id: uuid.UUID,
    episode_keys: list[str],
) -> defaultdict[str, list[Episode]]:
    """Fetch all non-deleted episodes for a plugin matching the given keys."""
    episodes_by_key: defaultdict[str, list[Episode]] = defaultdict(list)
    for episode in session.exec(
        select(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
        .where(Source.plugin_id == plugin_id)
        .where(col(Episode.key).in_(episode_keys))
        .where(col(Episode.deleted_at).is_(None)),
    ).all():
        episodes_by_key[episode.key].append(episode)
    return episodes_by_key


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
        if plugin_cls.implements("import_watch_history_instructions")
        and Plugin.get(session, plugin_user, plugin_cls.plugin_key())
    ]


def get_installed_plugin(plugin_key: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_key."""
    import_plugins()
    for plugin_cls in plugins:
        if plugin_cls.plugin_key() == plugin_key:
            return plugin_cls
    return None
