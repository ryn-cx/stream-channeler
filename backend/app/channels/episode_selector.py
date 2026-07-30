# TODO: Validate
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import String, case, literal_column
from sqlalchemy.orm import Mapped, aliased
from sqlalchemy.sql.expression import ColumnElement, UnaryExpression
from sqlmodel import and_, col, desc, func, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.auth.dependencies import CurrentUser, SessionDep
from app.channel_orders.models import ChannelOrder
from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelSavedEpisodeOrder,
    ChannelSeasonFilter,
    ChannelShow,
)
from app.channels.schemas import ChannelOptions, SortKeyInput
from app.episodes.models import Episode
from app.models import Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.sources.service import OTHER_SOURCE_KEY
from app.users.models import User
from app.users.schemas import SourcePreference
from app.users.service import effective_source_preferences, stored_preferences
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000

# Labels used to compose raw SQL references from Postgres subquery + column
# names. Callers of `literal_column` below rely on the producing subquery
# being materialised with exactly these names; keep them in sync.
EPISODE_LAST_WATCHED_SUBQUERY = "episode_last_watched"
EPISODE_LAST_WATCH_COMPLETED_COLUMN = "episode_last_watch_completed_date"
EPISODE_LAST_WATCH_INCOMPLETE_COLUMN = "episode_last_watch_incomplete_date"

# Maps each last-watched sort field to the subquery column holding its latest
# watch date. Aggregated per episode (not per show) so an episode is ranked by
# its own watch history. Completed = verified watches; incomplete = unverified
# (partial) watches.
LAST_WATCHED_COLUMNS = {
    "last_watched_completed": EPISODE_LAST_WATCH_COMPLETED_COLUMN,
    "last_watched_incomplete": EPISODE_LAST_WATCH_INCOMPLETE_COLUMN,
}


@dataclass
class SourceDedupConfig:
    """Resolved priority and enabled state used while selecting episodes."""

    priority: dict[str, int]
    other_priority: int
    disabled_keys: set[str]
    enabled_keys: set[str]
    other_enabled: bool

    def priority_for(self, plugin_key: str | None) -> int:
        """Return the priority of a plugin key, falling back to `Other`."""
        if plugin_key is None:
            return self.other_priority
        return self.priority.get(plugin_key, self.other_priority)


def source_dedup_config(stored: list[SourcePreference]) -> SourceDedupConfig:
    """Resolve a user's effective preferences into priorities and enabled sets."""
    preferences = effective_source_preferences(stored)
    priority = {
        preference.source_key: index for index, preference in enumerate(preferences)
    }
    disabled_keys = {
        preference.source_key
        for preference in preferences
        if not preference.enabled and preference.source_key != OTHER_SOURCE_KEY
    }
    enabled_keys = {
        preference.source_key
        for preference in preferences
        if preference.enabled and preference.source_key != OTHER_SOURCE_KEY
    }
    other_enabled = next(
        preference.enabled
        for preference in preferences
        if preference.source_key == OTHER_SOURCE_KEY
    )
    return SourceDedupConfig(
        priority=priority,
        other_priority=priority[OTHER_SOURCE_KEY],
        disabled_keys=disabled_keys,
        enabled_keys=enabled_keys,
        other_enabled=other_enabled,
    )


def deduplicate_episodes(
    episodes: list[Episode],
    plugin_key_by_episode_id: dict[UUID, str],
    config: SourceDedupConfig,
) -> list[Episode]:
    """Return `episodes` with no repeated `episode_identifier`.

    Among episodes that share an identifier the highest-priority source wins, while
    the original ordering is preserved by first occurrence.
    """

    def priority(episode: Episode) -> int:
        return config.priority_for(plugin_key_by_episode_id.get(episode.id))

    best_by_identifier: dict[str, Episode] = {}
    for episode in episodes:
        identifier = episode.episode_identifier
        current = best_by_identifier.get(identifier)
        if current is None or priority(episode) < priority(current):
            best_by_identifier[identifier] = episode

    deduplicated: list[Episode] = []
    seen: set[str] = set()
    for episode in episodes:
        identifier = episode.episode_identifier
        if identifier in seen:
            continue
        seen.add(identifier)
        deduplicated.append(best_by_identifier[identifier])
    return deduplicated


@dataclass
class EpisodeResult:
    episode: Episode
    channel_id: UUID
    channel_ids: list[UUID]
    latest_watch: Watch | None = None


def _select_show_subset(
    show_order: list[tuple[UUID, bool]],
    total: int | None,
    started_count: int | None,
    new_count: int | None,
) -> set[UUID]:
    started_in_order = [show_id for show_id, is_started in show_order if is_started]
    new_in_order = [show_id for show_id, is_started in show_order if not is_started]

    if total is not None and started_count is None and new_count is None:
        return {show_id for show_id, _ in show_order[:total]}

    selected_started: list[UUID] | None = (
        started_in_order[:started_count] if started_count is not None else None
    )
    selected_new: list[UUID] | None = (
        new_in_order[:new_count] if new_count is not None else None
    )

    if selected_started is None:
        if total is None:
            selected_started = started_in_order
        else:
            remaining = max(0, total - len(selected_new or []))
            selected_started = started_in_order[:remaining]
    if selected_new is None:
        if total is None:
            selected_new = new_in_order
        else:
            remaining = max(0, total - len(selected_started))
            selected_new = new_in_order[:remaining]

    selected = set(selected_started) | set(selected_new)

    if total is not None and len(selected) > total:
        trimmed: set[UUID] = set()
        for show_id, _ in show_order:
            if show_id in selected:
                trimmed.add(show_id)
                if len(trimmed) >= total:
                    break
        selected = trimmed

    return selected


class _SortExpressionBuilder:
    def __init__(self, random_seed: int, user: User | None) -> None:
        self._random_seed = random_seed
        self._user = user

    def expression(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        if sort_key.field == "saved_order":
            return col(ChannelSavedEpisodeOrder.position)
        if sort_key.aggregation and sort_key.model == "episode":
            return self._aggregate_episode_expr(sort_key)
        return self._value_expr(sort_key)

    @staticmethod
    def apply_direction(
        expr: ColumnElement[Any],
        sort_key: SortKeyInput,
    ) -> UnaryExpression[Any] | ColumnElement[Any]:
        directed: UnaryExpression[Any] | ColumnElement[Any] = (
            desc(expr) if sort_key.direction == "descending" else expr
        )
        if sort_key.field in LAST_WATCHED_COLUMNS and sort_key.direction == "ascending":
            return directed.nulls_first()
        return directed.nulls_last()

    def random_hash(self, expr: ColumnElement[Any]) -> ColumnElement[Any]:
        return func.hashtext(
            func.concat(
                func.cast(expr, String),
                str(self._random_seed),
            ),
        )

    def _value_expr(self, sort_key: SortKeyInput) -> ColumnElement[Any]:  # noqa: PLR0911
        field = sort_key.field

        if field == "random":
            random_ids: dict[str, Any] = {
                "episode": Episode.id,
                "season": Season.id,
                "show": Show.id,
                "source": Source.id,
                "plugin": Plugin.id,
            }
            return self.random_hash(random_ids[sort_key.model])
        if field == "sequential":
            return self._sequential_rank(sort_key.model)
        if field == "recently_aired":
            return self._recently_aired_expr(sort_key)
        if field in LAST_WATCHED_COLUMNS:
            return literal_column(
                f"{EPISODE_LAST_WATCHED_SUBQUERY}.{LAST_WATCHED_COLUMNS[field]}",
            )
        if field == "episode_count":
            return func.count(Episode.id).over(partition_by=col(Show.id))  # type: ignore[arg-type]
        if field == "started" and sort_key.model == "show":
            return self._started_show_expr()

        return getattr(sort_key.model_class, field)  # type: ignore[no-any-return]

    def _aggregate_episode_expr(
        self,
        sort_key: SortKeyInput,
    ) -> ColumnElement[Any]:
        if sort_key.field in LAST_WATCHED_COLUMNS:
            return literal_column(
                f"{EPISODE_LAST_WATCHED_SUBQUERY}.{LAST_WATCHED_COLUMNS[sort_key.field]}",
            )

        if sort_key.field == "random":
            episode_field: ColumnElement[Any] = self.random_hash(Show.id)  # type: ignore[arg-type]
        elif sort_key.field == "recently_aired":
            episode_field = self._recently_aired_expr(sort_key)
        elif sort_key.field == "episode_count":
            episode_field = Episode.id  # type: ignore[assignment]
        else:
            episode_field = getattr(Episode, sort_key.field)

        agg_funcs: dict[str, Any] = {
            "max": func.max,
            "min": func.min,
            "avg": func.avg,
        }
        agg_func = agg_funcs.get(sort_key.aggregation)  # type: ignore[arg-type]
        if agg_func is None:
            msg = f"Unsupported aggregation '{sort_key.aggregation}'"
            raise ValueError(msg)
        return agg_func(episode_field).over(partition_by=col(Show.id))

    @staticmethod
    def _sequential_rank(model: str) -> ColumnElement[Any]:
        """Dense rank computed inline so filters like hide_watched shrink it.

        Emitted as a window function in the post-filter subquery rather than
        a pre-aggregated sibling query, which means the rank reflects
        position within the visible set rather than position within the
        full table.
        """
        if model == "episode":
            return func.dense_rank().over(
                partition_by=col(Episode.season_id),
                order_by=col(Episode.episode_number),
            )
        if model == "season":
            return func.dense_rank().over(
                partition_by=col(Season.show_id),
                order_by=(
                    col(Season.season_number),
                    case(
                        (
                            col(Season.season_number).is_not(None),
                            col(Season.sort_order),
                        ),
                    ),
                ),
            )
        msg = f"sequential is not supported for model '{model}'"
        raise ValueError(msg)

    @staticmethod
    def _recently_aired_expr(sort_key: SortKeyInput) -> ColumnElement[Any]:
        cutoff = sort_key.recently_aired_date or (
            tz_datetime.now() - timedelta(days=sort_key.days or 7)
        )
        return case(
            (
                and_(
                    col(Episode.air_date).is_not(None),
                    col(Episode.air_date) >= cutoff,
                ),
                1,
            ),
            else_=0,
        )

    def _started_show_expr(self) -> ColumnElement[Any]:
        if not self._user:
            return literal_column("0")
        started_query = (
            select(Watch.id)
            .join(Episode, Watch.episode_identifier == Episode.episode_identifier)  # type: ignore[arg-type]
            .join(Season, Episode.season_id == Season.id)  # type: ignore[arg-type]
            .where(
                and_(
                    col(Season.show_id) == col(Show.id),
                    Watch.user_id == self._user.id,
                ),
            )
            .correlate(Show)
            .limit(1)
        )
        return case((started_query.exists(), 1), else_=0)


def child_channel_ids(channel: Channel) -> list[UUID]:
    """Return the additional channel ids combined into a channel, in order."""
    return [combined.combined_channel_id for combined in channel.combined_channels]


def readable_channels(
    session: SessionDep,
    user: User | None,
    channel_ids: Collection[UUID],
) -> Sequence[Channel]:
    """Return the channels the user is allowed to read from the given ids."""
    query = select(Channel).where(col(Channel.id).in_(channel_ids))
    readable = col(Channel.visibility).in_(
        (Visibility.public, Visibility.unlisted),
    )
    if user is None:
        query = query.where(readable)
    elif not user.is_superuser:
        query = query.where(or_(readable, col(Channel.user_id) == user.id))

    return session.exec(query).all()


def resolve_channel_ids(
    session: SessionDep,
    user: User | None,
    main_channel: Channel,
    additional_channels: Collection[UUID],
) -> set[UUID]:
    """Resolve the full set of readable channel ids reachable from a channel.

    Starts from the main channel plus `additional_channels` and follows each
    readable channel's children (its own `additional_channels`) recursively.
    """
    all_channel_ids = {main_channel.id}
    queued_channel_ids = {main_channel.id}
    to_expand = set(additional_channels) - queued_channel_ids

    while to_expand:
        queued_channel_ids.update(to_expand)
        children: set[UUID] = set()
        for channel in readable_channels(session, user, to_expand):
            all_channel_ids.add(channel.id)
            children.update(child_channel_ids(channel))
        to_expand = children - queued_channel_ids

    return all_channel_ids


class EpisodeQueryBuilder:
    def __init__(
        self,
        session: SessionDep,
        channel: Channel,
        channel_options: ChannelOptions,
        user: CurrentUser | None = None,
    ) -> None:
        self._session = session
        self._user = user
        self._now = tz_datetime.now()
        self._main_channel_id = channel.id
        channel_options = self._resolve_order_preset(channel_options)
        self._channel_options = self._filter_channel_options(channel_options)
        self._channel_ids = self._resolve_channel_ids(channel)
        self._source_config: SourceDedupConfig = source_dedup_config(
            stored_preferences(self._user.source_preferences) if self._user else [],
        )
        self._sort_expressions = _SortExpressionBuilder(
            random_seed=self._channel_options.random_seed,
            user=self._user,
        )

    def _require_user(self) -> User:
        if self._user is None:
            msg = "This operation requires an authenticated user."
            raise ValueError(msg)
        return self._user

    def _resolve_order_preset(
        self,
        channel_options: ChannelOptions,
    ) -> ChannelOptions:
        """Replace the channel's options with a referenced `ChannelOrder` preset."""
        if channel_options.order_preset_id is None:
            return channel_options
        order = self._session.exec(
            select(ChannelOrder).where(
                ChannelOrder.id == channel_options.order_preset_id,
            ),
        ).first()
        if order is None:
            return channel_options
        preset = ChannelOptions.model_validate_json(order.config)
        # Only override the options the preset actually stored so older presets that
        # only captured sorting leave the channel's other options untouched.
        update = {
            name: getattr(preset, name)
            for name in preset.model_fields_set
            if name != "order_preset_id"
        }
        return channel_options.model_copy(update=update)

    def _filter_channel_options(
        self,
        channel_options: ChannelOptions,
    ) -> ChannelOptions:
        """Filter options that require authentication if the user is not authenticated

        Allows an authenticated user to share a URL with an unauthenticated user even if
        the channel options include options that only authenticated users can use.
        """
        if self._user is not None:
            return channel_options
        return channel_options.model_copy(
            update={
                # last_watched sort keys need the user's watch history.
                "sort_by": [
                    sort_key
                    for sort_key in channel_options.sort_by
                    if sort_key.field not in LAST_WATCHED_COLUMNS
                ],
                "hide_watched": False,
                "hide_unwatched": False,
                "hide_partially_watched": False,
                "maximum_watch_date_absolute": None,
                "maximum_watch_date_relative": None,
                "total_shows_count": None,
                "started_shows_count": None,
                "new_shows_count": None,
            },
        )

    def _resolve_channel_ids(self, main_channel: Channel) -> set[UUID]:
        return resolve_channel_ids(
            self._session,
            self._user,
            main_channel,
            child_channel_ids(main_channel),
        )

    def get_episodes(self) -> list[EpisodeResult]:
        """Get filtered, sorted episodes with channel IDs and latest watch data."""
        query = self._base_query()
        query = self._join_whitelist(query)
        query = self._join_episode_last_watched(query)
        query = self._join_saved_order(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._apply_channel_specific_blacklist(query)
        query = self._filter_by_plugin_visibility(query)
        query = self._filter_disabled_sources(query)
        query = self._filter_watched_episodes(query)
        query = self._filter_unwatched_episodes(query)
        query = self._filter_partially_watched_episodes(query)
        query = self._filter_by_ranges(query)
        query = self._sort_episodes(query)
        query = self._apply_limit(query)

        ordered_episodes: list[Episode] = []
        channels_by_episode: dict[UUID, list[UUID]] = {}
        for episode, channel_id in self._session.exec(query).all():
            if episode.id not in channels_by_episode:
                channels_by_episode[episode.id] = []
                ordered_episodes.append(episode)
            if channel_id not in channels_by_episode[episode.id]:
                channels_by_episode[episode.id].append(channel_id)

        ordered_episodes = self._deduplicate_by_identifier(ordered_episodes)
        ordered_episodes = self._apply_show_count_selection(ordered_episodes)
        ordered_episodes = ordered_episodes[: self._result_limit()]

        watches = self._get_latest_watches(ordered_episodes)
        return [
            EpisodeResult(
                episode=episode,
                channel_id=channels_by_episode[episode.id][0],
                channel_ids=channels_by_episode[episode.id],
                latest_watch=watches.get(episode.episode_identifier),
            )
            for episode in ordered_episodes
        ]

    def _get_latest_watches(
        self,
        episodes: Sequence[Episode],
    ) -> dict[str, Watch]:
        """Get the latest watch keyed by `episode_identifier`."""
        if not self._user or not episodes:
            return {}

        identifiers = [episode.episode_identifier for episode in episodes]
        watches = self._session.exec(
            select(Watch)
            .where(
                col(Watch.episode_identifier).in_(identifiers),
                Watch.user_id == self._user.id,
            )
            .order_by(
                col(Watch.episode_identifier),
                desc(Watch.watch_date),
                desc(Watch.id),
            )
            .distinct(col(Watch.episode_identifier)),
        ).all()

        return {watch.episode_identifier: watch for watch in watches}

    def _base_query(self) -> Select[tuple[Episode, UUID]]:
        return (
            select(Episode, ChannelShow.channel_id)  # type: ignore[call-overload]
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
        )

    def _join_whitelist(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return query.outerjoin(
            ChannelSeasonFilter,
            and_(
                ChannelSeasonFilter.channel_show_id == ChannelShow.id,
                ChannelSeasonFilter.season_id == Season.id,
            ),
        ).outerjoin(
            ChannelEpisodeFilter,
            and_(
                ChannelEpisodeFilter.channel_show_id == ChannelShow.id,
                ChannelEpisodeFilter.episode_id == Episode.id,
                or_(
                    col(ChannelEpisodeFilter.expires_at).is_(None),
                    col(ChannelEpisodeFilter.expires_at) > self._now,
                ),
            ),
        )

    def _join_saved_order(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        needs_saved_order = any(
            key.field == "saved_order" for key in self._channel_options.sort_by
        )
        if not needs_saved_order:
            return query
        return query.outerjoin(
            ChannelSavedEpisodeOrder,
            and_(
                ChannelSavedEpisodeOrder.channel_id == self._main_channel_id,
                ChannelSavedEpisodeOrder.episode_id == Episode.id,
            ),
        )

    def _join_episode_last_watched(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        needs_last_watched = any(
            key.field in LAST_WATCHED_COLUMNS for key in self._channel_options.sort_by
        )
        if not needs_last_watched or not self._user:
            return query

        episode_last_watched_subquery = (
            select(
                Watch.episode_identifier,
                func.max(
                    case((col(Watch.verified).is_(True), Watch.watch_date)),
                ).label(EPISODE_LAST_WATCH_COMPLETED_COLUMN),
                func.max(
                    case((col(Watch.verified).is_(False), Watch.watch_date)),
                ).label(EPISODE_LAST_WATCH_INCOMPLETE_COLUMN),
            )
            .select_from(Watch)
            .where(col(Watch.user_id) == self._user.id)
            .group_by(col(Watch.episode_identifier))
            .subquery(EPISODE_LAST_WATCHED_SUBQUERY)
        )

        return query.outerjoin(
            episode_last_watched_subquery,
            col(Episode.episode_identifier)
            == episode_last_watched_subquery.c.episode_identifier,
        )

    @staticmethod
    def _parse_date_filter(
        absolute_date: datetime | None,
        relative_days: int | None,
    ) -> datetime | None:
        if relative_days:
            return tz_datetime.now() - timedelta(days=relative_days)
        return absolute_date

    def _filter_deleted_media(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return query.where(col(Episode.deleted_at).is_(None))

    def _filter_by_plugin_visibility(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Filter out episodes from private plugins the viewer doesn't own."""
        conditions: list[ColumnElement[bool]] = [
            col(Plugin.visibility).in_((Visibility.public, Visibility.unlisted)),
        ]
        if self._user:
            conditions.append(col(Plugin.user_id) == self._user.id)  # type: ignore[arg-type]
        query = (
            query.join(Source, col(Show.source_id) == Source.id)
            .join(Plugin, col(Source.plugin_id) == Plugin.id)
            .where(or_(*conditions))
        )
        if self._channel_options.source_ids:
            if self._channel_options.source_ids_is_blacklist:
                query = query.where(
                    col(Source.id).not_in(self._channel_options.source_ids),
                )
            else:
                query = query.where(
                    col(Source.id).in_(self._channel_options.source_ids),
                )
        return query

    @staticmethod
    def _channel_access_condition() -> ColumnElement[bool]:
        return or_(
            and_(
                col(ChannelShow.is_whitelist).is_(True),
                or_(
                    and_(
                        col(ChannelSeasonFilter.season_id).is_not(None),
                        col(ChannelEpisodeFilter.episode_id).is_(None),
                    ),
                    and_(
                        col(ChannelSeasonFilter.season_id).is_(None),
                        col(ChannelEpisodeFilter.episode_id).is_not(None),
                    ),
                ),
            ),
            and_(
                col(ChannelShow.is_whitelist).is_(False),
                or_(
                    and_(
                        col(ChannelSeasonFilter.season_id).is_(None),
                        col(ChannelEpisodeFilter.episode_id).is_(None),
                    ),
                    and_(
                        col(ChannelSeasonFilter.season_id).is_not(None),
                        col(ChannelEpisodeFilter.episode_id).is_not(None),
                    ),
                ),
            ),
        )

    def _filter_episodes_by_channels(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return (
            query.where(col(ChannelShow.channel_id).in_(self._channel_ids))
            # Only member shows contribute their episodes; filter-only shows
            # (is_blacklist_only=True) exist solely to hold blacklist/whitelist entries.
            .where(col(ChannelShow.is_blacklist_only).is_(False))
            .where(self._channel_access_condition())
        )

    def _apply_channel_specific_blacklist(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        filter_only_show = aliased(ChannelShow)
        filter_only_filter = aliased(ChannelEpisodeFilter)
        blacklisted_episodes = (
            select(filter_only_filter.episode_id)
            .select_from(filter_only_filter)
            .join(
                filter_only_show,
                col(filter_only_filter.channel_show_id) == filter_only_show.id,
            )
            .where(
                col(filter_only_show.is_blacklist_only).is_(True),
                col(filter_only_show.channel_id).in_(self._channel_ids),
                filter_only_filter.episode_id == Episode.id,
                or_(
                    col(filter_only_filter.expires_at).is_(None),
                    col(filter_only_filter.expires_at) > self._now,
                ),
            )
        )
        return query.where(~blacklisted_episodes.exists())

    def _verified_watches_subquery(self) -> SelectOfScalar[str]:
        user = self._require_user()
        return select(Watch.episode_identifier).where(
            and_(
                Watch.user_id == user.id,
                col(Watch.verified).is_(True),
            ),
        )

    def _any_watches_subquery(self) -> SelectOfScalar[str]:
        """Episode identifiers with any watch (verified or not) for the user."""
        user = self._require_user()
        return select(Watch.episode_identifier).where(Watch.user_id == user.id)

    def _hide_watched_condition(self) -> ColumnElement[bool] | None:
        # Watched = has a verified watch. Partially watched (unverified) and
        # unwatched episodes are kept.
        if not (self._user and self._channel_options.hide_watched):
            return None
        watched_subquery = self._verified_watches_subquery()
        absolute_date = self._channel_options.maximum_watch_date_absolute
        relative_date = self._channel_options.maximum_watch_date_relative
        if max_watch_date := self._parse_date_filter(absolute_date, relative_date):
            watched_subquery = watched_subquery.where(
                Watch.watch_date > max_watch_date,
            )
        return col(Episode.episode_identifier).not_in(watched_subquery)

    def _hide_unwatched_condition(self) -> ColumnElement[bool] | None:
        # Unwatched = no watch at all. Partially watched (unverified) and verified
        # episodes are kept.
        if not (self._user and self._channel_options.hide_unwatched):
            return None
        return col(Episode.episode_identifier).in_(self._any_watches_subquery())

    def _hide_partially_watched_condition(self) -> ColumnElement[bool] | None:
        # Partially watched = has a watch but none verified. Unwatched and verified
        # episodes are kept.
        if not (self._user and self._channel_options.hide_partially_watched):
            return None
        return or_(
            col(Episode.episode_identifier).not_in(self._any_watches_subquery()),
            col(Episode.episode_identifier).in_(self._verified_watches_subquery()),
        )

    def _filter_watched_episodes(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        condition = self._hide_watched_condition()
        if condition is None:
            return query
        return query.where(condition)

    def _filter_unwatched_episodes(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        condition = self._hide_unwatched_condition()
        if condition is None:
            return query
        return query.where(condition)

    def _filter_partially_watched_episodes(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        condition = self._hide_partially_watched_condition()
        if condition is None:
            return query
        return query.where(condition)

    def _started_shows_subquery(self) -> SelectOfScalar[UUID]:
        user = self._require_user()
        return (
            select(Show.id)
            .join(Season, col(Show.id) == Season.show_id)
            .join(Episode, col(Season.id) == Episode.season_id)
            .join(
                Watch,
                and_(
                    Watch.episode_identifier == Episode.episode_identifier,
                    Watch.user_id == user.id,
                ),
            )
            .distinct()
        )

    def _apply_show_count_selection(
        self,
        episodes: list[Episode],
    ) -> list[Episode]:
        total = self._channel_options.total_shows_count
        started_count = self._channel_options.started_shows_count
        new_count = self._channel_options.new_shows_count
        if total is None and started_count is None and new_count is None:
            return episodes
        if not self._user or not episodes:
            return episodes

        season_ids = {episode.season_id for episode in episodes}
        season_to_show: dict[UUID, UUID] = dict(
            self._session.exec(
                select(Season.id, Season.show_id).where(
                    col(Season.id).in_(season_ids),
                ),
            ).all(),
        )
        started_show_ids: set[UUID] = set(
            self._session.exec(self._started_shows_subquery()).all(),
        )

        show_order: list[tuple[UUID, bool]] = []
        seen: set[UUID] = set()
        for episode in episodes:
            show_id = season_to_show[episode.season_id]
            if show_id in seen:
                continue
            seen.add(show_id)
            show_order.append((show_id, show_id in started_show_ids))

        selected = _select_show_subset(
            show_order,
            total=total,
            started_count=started_count,
            new_count=new_count,
        )
        return [
            episode
            for episode in episodes
            if season_to_show[episode.season_id] in selected
        ]

    def _episode_range_conditions(self) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []

        def add_range(
            column: ColumnElement[Any] | Mapped[Any],
            min_value: datetime | int | None,
            max_value: datetime | int | None,
        ) -> None:
            if min_value is not None:
                conditions.append(or_(column >= min_value, column.is_(None)))
            if max_value is not None:
                conditions.append(or_(column <= max_value, column.is_(None)))

        add_range(
            col(Episode.air_date),
            self._parse_date_filter(
                self._channel_options.minimum_air_date_absolute,
                self._channel_options.minimum_air_date_relative,
            ),
            self._parse_date_filter(
                self._channel_options.maximum_air_date_absolute,
                self._channel_options.maximum_air_date_relative,
            ),
        )
        add_range(
            col(Episode.release_date),
            self._parse_date_filter(
                self._channel_options.minimum_release_date_absolute,
                self._channel_options.minimum_release_date_relative,
            ),
            self._parse_date_filter(
                self._channel_options.maximum_release_date_absolute,
                self._channel_options.maximum_release_date_relative,
            ),
        )
        add_range(
            col(Episode.duration),
            self._channel_options.minimum_duration,
            self._channel_options.maximum_duration,
        )
        return conditions

    def _filter_by_ranges(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        for condition in self._episode_range_conditions():
            query = query.where(condition)
        return query

    def _result_limit(self) -> int:
        """The number of episodes to return after deduplication."""
        user_limit = self._channel_options.limit
        return min(user_limit or MAX_EPISODES_RETURNED, MAX_EPISODES_RETURNED)

    def _apply_limit(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        # Fetch up to the hard cap regardless of the requested limit so that
        # deduplication can still fill the requested number of unique episodes.
        return query.limit(MAX_EPISODES_RETURNED)

    def _filter_disabled_sources(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Globally hide episodes from sources the user has disabled.

        Stacks on top of the channel's own source filtering: an episode must pass
        both this and the per-channel `source_ids` filter. `Plugin` is already
        joined by `_filter_by_plugin_visibility`.
        """
        config = self._source_config
        if config.other_enabled:
            if config.disabled_keys:
                query = query.where(col(Plugin.key).not_in(config.disabled_keys))
        else:
            query = query.where(col(Plugin.key).in_(config.enabled_keys))
        return query

    def _plugin_keys_by_episode(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, str]:
        """Map each episode id to its owning plugin's key."""
        if not episodes:
            return {}
        rows = self._session.exec(
            select(Episode.id, Plugin.key)  # type: ignore[call-overload]
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .join(Plugin)
            .where(col(Episode.id).in_([episode.id for episode in episodes])),
        ).all()
        return dict(rows)

    def _deduplicate_by_identifier(
        self,
        episodes: list[Episode],
    ) -> list[Episode]:
        """Collapse episodes sharing an `episode_identifier` by source priority."""
        plugin_keys = self._plugin_keys_by_episode(episodes)
        return deduplicate_episodes(episodes, plugin_keys, self._source_config)

    def _sort_episodes(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        if not self._channel_options.sort_by:
            return query
        expressions = self._sort_expressions
        labeled_values: list[ColumnElement[Any]] = [
            expressions.expression(sort_key).label(f"sort_value_{index}")
            for index, sort_key in enumerate(self._channel_options.sort_by)
        ]
        labeled_values.append(col(Season.show_id).label("show_id"))
        subquery = query.add_columns(*labeled_values).subquery()

        raws = [
            getattr(subquery.c, f"sort_value_{i}")
            for i in range(len(self._channel_options.sort_by))
        ]
        directeds = [
            expressions.apply_direction(raws[i], key)
            for i, key in enumerate(self._channel_options.sort_by)
        ]

        fuzzy_indexes = [
            index
            for index, key in enumerate(self._channel_options.sort_by)
            if key.fuzziness
        ]
        fuzzy_labels = {index: f"fuzzy_{index}" for index in fuzzy_indexes}

        if fuzzy_indexes:
            extra_columns: list[ColumnElement[Any]] = [
                func.dense_rank()
                .over(order_by=directeds[index])
                .label(fuzzy_labels[index])
                for index in fuzzy_indexes
            ]
            subquery = (
                select(aliased(Episode, subquery), subquery.c.channel_id)
                .add_columns(
                    subquery.c.show_id,
                    *(getattr(subquery.c, f"sort_value_{i}") for i in range(len(raws))),
                    *extra_columns,
                )
                .subquery()
            )
            raws = [
                getattr(subquery.c, f"sort_value_{i}")
                for i in range(len(self._channel_options.sort_by))
            ]
            directeds = [
                expressions.apply_direction(raws[i], key)
                for i, key in enumerate(self._channel_options.sort_by)
            ]

        def fuzzy_expression(index: int) -> ColumnElement[Any]:
            sort_key = self._channel_options.sort_by[index]
            rank_column = getattr(subquery.c, fuzzy_labels[index])
            fuzziness = sort_key.fuzziness or 0
            jitter: ColumnElement[Any] = expressions.random_hash(subquery.c.id) * (
                fuzziness / float(2**31)
            )
            return rank_column + jitter

        order_by: list[UnaryExpression[Any] | ColumnElement[Any]] = []
        for index, sort_key in enumerate(self._channel_options.sort_by):
            if sort_key.order == "sequential":
                if sort_key.fuzziness:
                    order_by.append(fuzzy_expression(index))
                else:
                    order_by.append(directeds[index])
                continue

            row_num = func.row_number().over(
                partition_by=raws[: index + 1],
                order_by=directeds[index + 1 :] or [directeds[index]],
            )
            if sort_key.order == "randomize":
                partition_order: ColumnElement[Any] = expressions.random_hash(
                    raws[index],
                )
            elif sort_key.fuzziness:
                partition_order = fuzzy_expression(index)
            else:
                partition_order = directeds[index]
            order_by.extend([row_num, partition_order])

        order_by.extend([subquery.c.show_id, subquery.c.id])

        outer: Select[tuple[Episode, UUID]] = select(  # type: ignore[assignment]
            aliased(Episode, subquery),
            subquery.c.channel_id,
        )
        return outer.order_by(*order_by)
