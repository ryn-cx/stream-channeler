# TODO: Validate
import uuid
from collections.abc import Sequence

from sqlalchemy import ScalarSelect, Subquery
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.service.responses import get_read_results
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.titles.models import Title
from app.titles.schemas import TitlePublic
from app.tmdb_media.episodes import (
    links_of,
    tmdb_episode_id_column,
    tmdb_episode_link,
    tmdb_record_id_of,
)
from app.users.models import User
from app.watches.identifiers import (
    tmdb_record_id_by_watch,
    watch_names,
    watched_tmdb_record_ids,
)
from app.watches.models import Watch
from app.watches.schemas import (
    WatchesListOutput,
    WatchItem,
    WatchOutput,
)

# The episode a watch was recorded against, reached through the id the watch
WatchedEpisode = aliased(Episode)

# played it. Reads read it back to the episode that non-canonical row is of, so a watch
# counts across every source carrying that episode and goes on counting once the
# non-canonical row it was made against is gone.
IdentifiedEpisode = aliased(Episode)


# TODO: Validate
def _watched_tmdb_subquery(user_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    """Return the canonical episodes the `User` has watched anything of."""
    return watched_tmdb_record_ids(user_id)


# TODO: Validate
def _representative_episode_subquery(
    tmdb_record_ids: SelectOfScalar[uuid.UUID],
) -> Subquery:
    """One representative visible non-canonical row per canonical episode.

    A watch names the episode itself, which every website carrying it has a
    non-canonical row of. This picks a single visible non-canonical row per episode so a
    watch can be joined to concrete media for display and visibility filtering.
    Restricted to `tmdb_record_ids` so it only resolves the episodes actually in play
    instead of the whole episode catalog.

    TMDB is what a website's media is filled in from rather than a website an episode
    can be watched on, so its own non-canonical row is never what a watch is shown as,
    however the episodes happen to be ordered.
    """
    tmdb_link = tmdb_episode_link()
    return (
        select(
            col(tmdb_link.tmdb_episode_id).label("tmdb_episode_id"),
            col(Episode.id).label("episode_id"),
        )
        .join(tmdb_link, links_of(Episode, tmdb_link))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Title, col(Title.id) == col(Season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(Episode.deleted_at).is_(None))
        .where(col(Plugin.key) != TMDB_PLUGIN_KEY)
        .where(col(tmdb_link.tmdb_episode_id).in_(tmdb_record_ids))
        .distinct(col(tmdb_link.tmdb_episode_id))
        .order_by(col(tmdb_link.tmdb_episode_id), col(Episode.id))
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
        .join(Title, col(Title.id) == col(Season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
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
        _watched_tmdb_subquery(user_id),
    )
    identified_link = tmdb_episode_link()
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
            representative.c.tmdb_episode_id
            == tmdb_episode_id_column(IdentifiedEpisode, identified_link),
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
        .join(Title, col(Title.id) == col(Season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
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
        default_sorts=[Watch.watch_date],
        tiebreaker=Watch.id,
        params=read_options,
        current_user=user,
        extra_columns={
            "plugin": col(Plugin.key),
            "source": col(Source.key),
            "title": col(Title.name),
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
        .join(Title, col(Title.id) == col(Season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
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
    tmdb_record_ids_by_watch = tmdb_record_id_by_watch(
        session,
        [watch for watch in watches if watch.id not in episodes],
    )
    if not tmdb_record_ids_by_watch:
        return episodes
    representative = _representative_episode_subquery(
        select(col(Episode.id)).where(
            col(Episode.id).in_(set(tmdb_record_ids_by_watch.values())),
        ),
    )
    rows = session.exec(
        select(representative.c.tmdb_episode_id, Episode)
        .select_from(Episode)
        .join(representative, col(Episode.id) == representative.c.episode_id),
    ).all()
    episode_by_tmdb_record_id = dict(rows)
    for watch_id, tmdb_record_id in tmdb_record_ids_by_watch.items():
        episode = episode_by_tmdb_record_id.get(tmdb_record_id)
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
    titles_dict: dict[uuid.UUID, TitlePublic] = {}
    sources_dict: dict[uuid.UUID, SourcePublic] = {}
    plugins_dict: dict[uuid.UUID, PluginOutput] = {}
    watches: list[WatchItem] = []

    episode_by_watch = _representative_episodes_by_watch(session, episode_watches)

    for episode_watch in episode_watches:
        episode = episode_by_watch.get(episode_watch.id)
        if episode is None:
            continue
        season = episode.season
        title = season.title
        source = title.source
        plugin = source.plugin

        tmdb_episode_id = tmdb_record_id_of(episode)
        if tmdb_episode_id not in episodes_dict:
            episodes_dict[tmdb_episode_id] = EpisodeOutput.model_validate(
                episode,
            )
        if season.id not in seasons_dict:
            seasons_dict[season.id] = SeasonOutput.model_validate(season)
        if title.id not in titles_dict:
            titles_dict[title.id] = TitlePublic.model_validate(title)
        if source.id not in sources_dict:
            sources_dict[source.id] = SourcePublic.model_validate(source)
        if plugin.id not in plugins_dict:
            plugins_dict[plugin.id] = PluginOutput.model_validate(plugin)

        watches.append(
            WatchItem(
                id=episode_watch.id,
                episode_id=episode_watch.episode_id,
                tmdb_episode_id=tmdb_episode_id,
                watch_identifier=episode_watch.watch_identifier,
                watch_date=episode_watch.watch_date,
                verified=episode_watch.verified,
            ),
        )

    return WatchesListOutput(
        watches=watches,
        episodes=episodes_dict,
        seasons=seasons_dict,
        titles=titles_dict,
        sources=sources_dict,
        plugins=plugins_dict,
    )
