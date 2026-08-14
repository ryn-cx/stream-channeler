# TODO: Validate
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from sqlalchemy import ColumnElement, ScalarSelect, Subquery
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.media.identifiers import TMDB_PLUGIN_KEY
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
from app.watches.exceptions import WatchAlreadyExistsError
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

# The episode a watch was recorded against. Reads group watches by the canonical
# episode the watch itself names, so a watch counts across every source carrying
# that episode and goes on counting once the copy it was made against is gone.
WatchedEpisode = aliased(Episode)


# TODO: Validate
def _visible_plugin_condition(user_id: uuid.UUID) -> ColumnElement[bool]:
    return or_(
        col(Plugin.visibility).in_((Visibility.public, Visibility.unlisted)),
        col(Plugin.user_id) == user_id,
    )


# TODO: Validate
def _watched_canonical_subquery(user_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    """The canonical episodes the `User` has watched anything of."""
    return (
        select(col(Episode.id))
        .join(
            Watch,
            col(Watch.canonical_episode_key) == col(Episode.key),
        )
        .where(Watch.user_id == user_id)
    )


# TODO: Validate
def _representative_episode_subquery(
    user_id: uuid.UUID,
    canonical_ids: SelectOfScalar[uuid.UUID],
) -> Subquery:
    """One representative visible copy per canonical episode.

    A watch names the episode itself, which every website carrying it has a copy
    of. This picks a single visible copy per episode so a watch can be joined to
    concrete media for display and visibility filtering. Restricted to
    `canonical_ids` so it only resolves the episodes actually in play instead of
    the whole episode catalog.

    TMDB is what a website's media is filled in from rather than a website an
    episode can be watched on, so its own copy is never what a watch is shown
    as, however the episodes happen to be ordered.
    """
    return (
        select(
            col(Episode.canonical_episode_id).label("canonical_episode_id"),
            col(Episode.id).label("episode_id"),
        )
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(Episode.deleted_at).is_(None))
        .where(_visible_plugin_condition(user_id))
        .where(col(Plugin.key) != TMDB_PLUGIN_KEY)
        .where(col(Episode.canonical_episode_id).in_(canonical_ids))
        .distinct(col(Episode.canonical_episode_id))
        .order_by(col(Episode.canonical_episode_id), col(Episode.id))
        .subquery()
    )


# TODO: Validate
def _own_visible_episode_subquery(user_id: uuid.UUID) -> ScalarSelect[uuid.UUID]:
    """The episode a watch was recorded against, when it is one the `User` can see.

    A watch is made against one website's copy of an episode, which is the copy
    it should be shown as. It is only stood in for by another source's copy when
    the one it was made against is not the `User`'s to see.
    """
    return (
        select(col(WatchedEpisode.id))
        .join(Season, col(Season.id) == col(WatchedEpisode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(WatchedEpisode.id) == col(Watch.episode_id))
        .where(col(WatchedEpisode.deleted_at).is_(None))
        .where(_visible_plugin_condition(user_id))
        .where(col(Plugin.key) != TMDB_PLUGIN_KEY)
        .correlate(Watch)
        .scalar_subquery()
    )


# TODO: Validate
def _episode_watch_base_statement(user_id: uuid.UUID) -> SelectOfScalar[Watch]:
    representative = _representative_episode_subquery(
        user_id,
        _watched_canonical_subquery(user_id),
    )
    # Joined on the key the watch carries rather than through the copy it was
    # recorded against, so a watch whose copy has since been deleted is still
    # listed under another website's copy of the same episode.
    return (
        select(Watch)
        .join(
            Episode,
            col(Episode.key) == col(Watch.canonical_episode_key),
        )
        .join(
            representative,
            representative.c.canonical_episode_id == col(Episode.id),
        )
        .join(
            Episode,
            col(Episode.id)
            == func.coalesce(
                _own_visible_episode_subquery(user_id),
                representative.c.episode_id,
            ),
        )
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(Watch.user_id == user_id)
    )


# TODO: Validate
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


# TODO: Validate
def _representative_episodes_by_canonical_key(
    session: Session,
    user_id: uuid.UUID,
    canonical_keys: set[str],
) -> dict[str, Episode]:
    """Load the representative visible `Episode` for each watched key.

    Where the same media is reached two ways and so has a row under each, either
    stands for the key; they are copies of one episode either way.
    """
    if not canonical_keys:
        return {}
    canonical_ids = select(col(Episode.id)).where(
        col(Episode.key).in_(canonical_keys),
    )
    representative = _representative_episode_subquery(user_id, canonical_ids)
    rows = session.exec(
        select(col(Episode.key), Episode)  # type: ignore[call-overload]
        .join(representative, col(Episode.id) == representative.c.episode_id)
        .join(
            Episode,
            col(Episode.id) == col(Episode.canonical_episode_id),
        ),
    ).all()
    return dict(rows)


# TODO: Validate
def _format_watched_episodes_data(
    session: Session,
    user_id: uuid.UUID,
    episode_watches: Sequence[Watch],
) -> WatchesListOutput:
    episodes_dict: dict[uuid.UUID, EpisodeOutput] = {}
    seasons_dict: dict[uuid.UUID, SeasonOutput] = {}
    shows_dict: dict[uuid.UUID, ShowPublic] = {}
    sources_dict: dict[uuid.UUID, SourcePublic] = {}
    plugins_dict: dict[uuid.UUID, PluginOutput] = {}
    watches: list[WatchItem] = []

    episode_by_canonical_key = _representative_episodes_by_canonical_key(
        session,
        user_id,
        {watch.canonical_episode_key for watch in episode_watches},
    )

    for episode_watch in episode_watches:
        episode = episode_by_canonical_key.get(episode_watch.canonical_episode_key)
        if episode is None:
            continue
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        if episode.canonical_episode_id not in episodes_dict:
            episodes_dict[episode.canonical_episode_id] = EpisodeOutput.model_validate(
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
                canonical_episode_id=episode.canonical_episode_id,
                canonical_episode_key=episode_watch.canonical_episode_key,
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


# TODO: Validate
def create_watch(
    session: Session,
    user_id: uuid.UUID,
    episode: Episode,
    watch_input: WatchCreate,
) -> Watch:
    """Create a `Watch`.

    Raises:
        WatchAlreadyExistsError: If the `Episode` already has an unverified watch.
        ValueError: If the `Episode` is an episode rather than a copy of one.

    """
    # A watch is recorded against the episode rather than against the copy that
    # played it, so it is the episode's key that is stored. A copy that is of no
    # episode is one no import has reconciled, and there is nothing to record a
    # watch against.
    canonical_episode = episode.canonical_episode
    if canonical_episode is None:
        message = f"{episode} is an episode rather than a copy of one"
        raise ValueError(message)

    unverified_watch_query = select(Watch).where(
        Watch.user_id == user_id,
        col(Watch.canonical_episode_key) == canonical_episode.key,
        col(Watch.verified) == False,  # noqa: E712 - SQLAlchemy syntax
    )
    if session.exec(unverified_watch_query).first():
        message = "Episode already has an unverified watch. Verify or delete it first."
        raise WatchAlreadyExistsError(message)

    watch = Watch.model_validate(
        watch_input,
        update={
            "episode_id": episode.id,
            "canonical_episode_key": canonical_episode.key,
            "user_id": user_id,
        },
    )
    session.add(watch)
    session.commit()
    return watch


# TODO: Validate
def update_watch(
    session: Session,
    input_watch: Watch,
    watch_input: WatchUpdate,
) -> Watch:
    """Update a `Watch`."""
    return watch_input.update(session, input_watch)


# TODO: Validate
def delete_watches(session: Session, input_watch: Watch) -> Message:
    """Delete a `Watch`."""
    delete_record(session, input_watch)
    return Message(message="Watch deleted successfully")


# TODO: Validate
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


# TODO: Validate
def get_installed_plugin(plugin_key: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_key."""
    import_plugins()
    for plugin_cls in plugins:
        if plugin_cls.plugin_key() == plugin_key:
            return plugin_cls
    return None
