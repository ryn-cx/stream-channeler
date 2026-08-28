# TODO: Validate
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile
from sqlalchemy import ScalarSelect, Subquery
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    canonical_id_of,
    links_of,
)
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.media.service import delete_record
from app.plugins.identifiers import TMDB_PLUGIN_KEY
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
from app.watches.exceptions import WatchAlreadyExistsError
from app.watches.identifiers import (
    canonical_id_by_watch,
    watch_names,
    watched_canonical_ids,
    watches_of_canonical_ids,
)
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchesListOutput,
    WatchExportEntry,
    WatchImportInput,
    WatchImportResults,
    WatchItem,
    WatchOutput,
    WatchRelinkResults,
    WatchUpdate,
)
from plugins.StreamChanneler import StreamChanneler
from plugins.utils.manage_plugins import import_plugins, plugins

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import AbstractPlugin

# The episode a watch was recorded against, reached through the id the watch
# holds.
WatchedEpisode = aliased(Episode)

# The row carrying the identifier a watch holds, which is the non-canonical row that
# played it. Reads read it back to the episode that non-canonical row is of, so a watch
# counts across every source carrying that episode and goes on counting once the
# non-canonical row it was made against is gone.
IdentifiedEpisode = aliased(Episode)


# TODO: Validate
def _watched_canonical_subquery(user_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    """Return the canonical episodes the `User` has watched anything of."""
    return watched_canonical_ids(user_id)


# TODO: Validate
def _representative_episode_subquery(
    canonical_ids: SelectOfScalar[uuid.UUID],
) -> Subquery:
    """One representative visible non-canonical row per canonical episode.

    A watch names the episode itself, which every website carrying it has a
    non-canonical row of. This picks a single visible non-canonical row per episode so a
    watch can be joined to concrete media for display and visibility filtering.
    Restricted to `canonical_ids` so it only resolves the episodes actually in play
    instead of the whole episode catalog.

    TMDB is what a website's media is filled in from rather than a website an episode
    can be watched on, so its own non-canonical row is never what a watch is shown as,
    however the episodes happen to be ordered.
    """
    canonical_link = canonical_episode_link()
    return (
        select(
            col(canonical_link.canonical_episode_id).label("canonical_episode_id"),
            col(Episode.id).label("episode_id"),
        )
        .join(canonical_link, links_of(Episode, canonical_link))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(Episode.deleted_at).is_(None))
        .where(col(Plugin.key) != TMDB_PLUGIN_KEY)
        .where(col(canonical_link.canonical_episode_id).in_(canonical_ids))
        .distinct(col(canonical_link.canonical_episode_id))
        .order_by(col(canonical_link.canonical_episode_id), col(Episode.id))
        .subquery()
    )


# TODO: Validate
def _own_visible_episode_subquery() -> ScalarSelect[uuid.UUID]:
    """Return the episode a watch was recorded against, when the `User` can see it.

    A watch is made against one website's non-canonical row of an episode, which is the
    non-canonical row it should be shown as. It is only stood in for by another source's
    non-canonical row when the one it was made against is not the `User`'s to see.
    """
    return (
        select(col(WatchedEpisode.id))
        .join(Season, col(Season.id) == col(WatchedEpisode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(WatchedEpisode.id) == col(Watch.episode_id))
        .where(col(WatchedEpisode.deleted_at).is_(None))
        .where(col(Plugin.key) != TMDB_PLUGIN_KEY)
        .correlate(Watch)
        .scalar_subquery()
    )


# TODO: Validate
def _episode_watch_base_statement(user_id: uuid.UUID) -> SelectOfScalar[Watch]:
    representative = _representative_episode_subquery(
        _watched_canonical_subquery(user_id),
    )
    identified_link = canonical_episode_link()
    # Joined on the identifier the watch carries rather than through the link it was
    # recorded against, so a watch whose link has since been deleted is still listed
    # under another website's link to the same episode. The identifier is a link's own,
    # so it is read to the episode that link is of before the non-canonical row to show
    # it as is picked.
    return (
        select(Watch)
        .join(IdentifiedEpisode, watch_names(IdentifiedEpisode))
        .outerjoin(identified_link, links_of(IdentifiedEpisode, identified_link))
        .join(
            representative,
            representative.c.canonical_episode_id
            == canonical_episode_id_column(IdentifiedEpisode, identified_link),
        )
        .join(
            Episode,
            col(Episode.id)
            == func.coalesce(
                _own_visible_episode_subquery(),
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
    output = _format_watched_episodes_data(session, rows)
    output.total_count = total_count
    output.filtered_count = filtered_count
    output.is_server_side = is_server_side
    return output


# TODO: Validate
def _own_visible_episodes_by_watch(
    session: Session,
    watches: Sequence[Watch],
) -> dict[uuid.UUID, Episode]:
    watch_ids = {watch.id for watch in watches}
    if not watch_ids:
        return {}
    rows = session.exec(
        select(col(Watch.id), Episode)  # type: ignore[call-overload]
        .select_from(Watch)
        .join(Episode, col(Episode.id) == col(Watch.episode_id))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Watch.id).in_(watch_ids),
            col(Episode.deleted_at).is_(None),
            col(Plugin.key) != TMDB_PLUGIN_KEY,
        ),
    ).all()
    return dict(rows)


# TODO: Validate
def _representative_episodes_by_watch(
    session: Session,
    watches: Sequence[Watch],
) -> dict[uuid.UUID, Episode]:
    """Load the representative visible `Episode` for each watched identifier.

    An identifier is a link's own, so it is read to the episode that link is of and the
    non-canonical row to show it as is picked from that episode's links. Where the same
    media is reached two ways and so has a row under each, either stands for the
    identifier; they are links to one episode either way.
    """
    episodes = _own_visible_episodes_by_watch(session, watches)
    canonical_ids_by_watch = canonical_id_by_watch(
        session,
        [watch for watch in watches if watch.id not in episodes],
    )
    if not canonical_ids_by_watch:
        return episodes
    representative = _representative_episode_subquery(
        select(col(Episode.id)).where(
            col(Episode.id).in_(set(canonical_ids_by_watch.values())),
        ),
    )
    rows = session.exec(
        select(representative.c.canonical_episode_id, Episode)
        .select_from(Episode)
        .join(representative, col(Episode.id) == representative.c.episode_id),
    ).all()
    episode_by_canonical_id = dict(rows)
    for watch_id, canonical_id in canonical_ids_by_watch.items():
        episode = episode_by_canonical_id.get(canonical_id)
        if episode is not None:
            episodes[watch_id] = episode
    return episodes


# TODO: Validate
def _format_watched_episodes_data(
    session: Session,
    episode_watches: Sequence[Watch],
) -> WatchesListOutput:
    episodes_dict: dict[uuid.UUID, EpisodeOutput] = {}
    seasons_dict: dict[uuid.UUID, SeasonOutput] = {}
    shows_dict: dict[uuid.UUID, ShowPublic] = {}
    sources_dict: dict[uuid.UUID, SourcePublic] = {}
    plugins_dict: dict[uuid.UUID, PluginOutput] = {}
    watches: list[WatchItem] = []

    episode_by_watch = _representative_episodes_by_watch(session, episode_watches)

    for episode_watch in episode_watches:
        episode = episode_by_watch.get(episode_watch.id)
        if episode is None:
            continue
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        canonical_episode_id = canonical_id_of(episode)
        if canonical_episode_id not in episodes_dict:
            episodes_dict[canonical_episode_id] = EpisodeOutput.model_validate(
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
                canonical_episode_id=canonical_episode_id,
                watch_identifier=episode_watch.watch_identifier,
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

    """
    # A watch is recorded against the link that played it, so it is that link's
    # own identifier that is stored. What it counts for is worked out on the way
    # back out, where the identifier is read to the episode the link is of and
    # every other link to that episode counts too.
    canonical_id = canonical_id_of(episode)

    unverified_watch_query = watches_of_canonical_ids(user_id, [canonical_id]).where(
        col(Watch.verified) == False,  # noqa: E712 - SQLAlchemy syntax
    )
    if session.exec(unverified_watch_query).first():
        message = "Episode already has an unverified watch. Verify or delete it first."
        raise WatchAlreadyExistsError(message)

    watch = Watch.model_validate(
        watch_input,
        update={
            "episode_id": episode.id,
            "watch_identifier": episode.watch_identifier,
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
def relink_detached_watches(session: Session) -> WatchRelinkResults:
    """Point every watch left without an episode back at one.

    A watch names what it played rather than the row it was recorded against,
    so one whose episode has since been deleted is attached again as soon as
    another link to that episode exists. Where several do, the `User`'s own
    source order picks between them, exactly as playback would.
    """
    # `relink_watches` loads the models as it is imported, so it is imported
    # where it is used rather than alongside the models it maps.
    from app.tools.relink_watches import relink_watches  # noqa: PLC0415

    detached = session.exec(
        select(func.count()).select_from(Watch).where(col(Watch.episode_id).is_(None)),
    ).one()
    return WatchRelinkResults(detached=detached, relinked=relink_watches(session))


# TODO: Validate
def get_plugins_with_import_watch_history(
    session: Session,
) -> list[type[AbstractPlugin]]:
    """Return all plugin classes that support watch import."""
    import_plugins()
    return [
        plugin_cls
        for plugin_cls in plugins
        if plugin_cls.implements("import_watch_history")
        and Plugin.get(session, plugin_cls.plugin_key())
    ]


# TODO: Validate
def get_installed_plugin(plugin_key: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_key."""
    import_plugins()
    for plugin_cls in plugins:
        if plugin_cls.plugin_key() == plugin_key:
            return plugin_cls
    return None


# TODO: Validate
def import_watch_history_file(
    session: Session,
    current_user: User,
    file: UploadFile,
    params: WatchImportInput,
) -> WatchImportResults:
    """Read a watch history a plugin wrote out and record what it says."""
    plugin = get_installed_plugin(params.plugin_key)
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {params.plugin_key!r} not found.",
        )
    if not plugin.implements("import_watch_history"):
        raise HTTPException(
            status_code=422,
            detail=f"Plugin {params.plugin_key!r} does not support watch history import.",
        )

    result = plugin(session=session).import_watch_history(
        content=file.file.read().decode("utf-8"),
        user=current_user,
        new_only=params.new_only,
        verified=params.verified,
    )
    session.commit()
    return result


# TODO: Validate
def export_watch_history_entries(
    session: Session,
    current_user: User,
) -> list[WatchExportEntry]:
    """Write out the `User`'s watches as a Stream Channeler watch history."""
    return StreamChanneler(session=session).export_watch_history(current_user)
