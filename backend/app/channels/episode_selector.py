# TODO: Validate
import random
from collections.abc import Sequence
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
from app.channels.models import (
    Channel,
    ChannelEpisodeWhiteList,
    ChannelSeasonWhiteList,
    ChannelShow,
)
from app.channels.schemas import ChannelOptions, SortKeyInput
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000

# Labels used to compose raw SQL references from Postgres subquery + column
# names. Callers of ``literal_column`` below rely on the producing subquery
# being materialised with exactly these names; keep them in sync.
SHOW_LAST_WATCHED_SUBQUERY = "show_last_watched"
SHOW_LAST_WATCH_DATE_COLUMN = "show_last_watch_date"
EPISODE_RANK_SUBQUERY = "episode_rank"
SEASON_RANK_SUBQUERY = "season_rank"
RANK_COLUMN = "rank"


@dataclass
class EpisodeResult:
    episode: Episode
    channel_id: UUID
    latest_watch: Watch | None = None


def _select_show_subset(  # noqa: PLR0913
    *,
    started_available: set[UUID],
    new_available: set[UUID],
    total: int | None,
    started_count: int | None,
    new_count: int | None,
    random_seed: int,
) -> set[UUID]:
    rng = random.Random(random_seed)  # noqa: S311
    started_list = list(started_available)
    new_list = list(new_available)
    rng.shuffle(started_list)
    rng.shuffle(new_list)

    if total is not None and started_count is None and new_count is None:
        combined = started_list + new_list
        rng.shuffle(combined)
        return set(combined[:total])

    selected_started: set[UUID] | None = (
        set(started_list[:started_count]) if started_count is not None else None
    )
    selected_new: set[UUID] | None = (
        set(new_list[:new_count]) if new_count is not None else None
    )

    if selected_started is None:
        if total is None:
            selected_started = set(started_list)
        else:
            remaining = max(0, total - len(selected_new or set()))
            selected_started = set(started_list[:remaining])
    if selected_new is None:
        if total is None:
            selected_new = set(new_list)
        else:
            remaining = max(0, total - len(selected_started))
            selected_new = set(new_list[:remaining])

    combined_set = selected_started | selected_new
    if total is not None and len(combined_set) > total:
        combined_list = list(combined_set)
        rng.shuffle(combined_list)
        combined_set = set(combined_list[:total])
    return combined_set


class _SortExpressionBuilder:
    def __init__(self, random_seed: int, user: User | None) -> None:
        self._random_seed = random_seed
        self._user = user

    def expression(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
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
        if sort_key.field == "last_watched" and sort_key.direction == "ascending":
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
            random_ids: dict[str, Mapped[UUID]] = {
                "episode": Episode.id,  # type: ignore[dict-item]
                "season": Season.id,  # type: ignore[dict-item]
                "show": Show.id,  # type: ignore[dict-item]
            }
            return self.random_hash(random_ids[sort_key.model])
        if field == "sequential":
            return self._sequential_rank(sort_key.model)
        if field == "recently_aired":
            return self._recently_aired_expr(sort_key)
        if field == "last_watched":
            return literal_column(
                f"{SHOW_LAST_WATCHED_SUBQUERY}.{SHOW_LAST_WATCH_DATE_COLUMN}",
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
        if sort_key.field == "last_watched":
            return literal_column(
                f"{SHOW_LAST_WATCHED_SUBQUERY}.{SHOW_LAST_WATCH_DATE_COLUMN}",
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
        if model == "episode":
            return literal_column(f"{EPISODE_RANK_SUBQUERY}.{RANK_COLUMN}")
        if model == "season":
            return literal_column(f"{SEASON_RANK_SUBQUERY}.{RANK_COLUMN}")
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
            .join(Episode, Watch.episode_id == Episode.id)  # type: ignore[arg-type]
            .join(Season, Episode.season_id == Season.id)  # type: ignore[arg-type]
            .where(
                and_(
                    col(Season.show_id) == col(Show.id),
                    Watch.user_id == self._user.id,
                    col(Watch.verified).is_(True),
                ),
            )
            .correlate(Show)
            .limit(1)
        )
        return case((started_query.exists(), 1), else_=0)


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
        self._channel_options = self._filter_channel_options(channel_options)
        self._channel_ids = self._resolve_channel_ids(channel)
        self._sort_expressions = _SortExpressionBuilder(
            random_seed=self._channel_options.random_seed,
            user=self._user,
        )

    def _require_user(self) -> User:
        if self._user is None:
            msg = "This operation requires an authenticated user."
            raise ValueError(msg)
        return self._user

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
                # last_watched sort key needs the user's watch history.
                "sort_by": [
                    sort_key
                    for sort_key in channel_options.sort_by
                    if sort_key.field != "last_watched"
                ],
                "hide_watched": False,
                "hide_unwatched": False,
                "maximum_watch_date_absolute": None,
                "maximum_watch_date_relative": None,
                "total_shows_count": None,
                "started_shows_count": None,
                "new_shows_count": None,
            },
        )

    def _resolve_channel_ids(self, main_channel: Channel) -> list[UUID]:
        additional_channel_ids = self._channel_options.additional_channels
        if not additional_channel_ids:
            return [main_channel.id]

        query = select(Channel.id).where(col(Channel.id).in_(additional_channel_ids))
        if self._user is None:
            query = query.where(col(Channel.public).is_(True))
        elif not self._user.is_superuser:
            query = query.where(
                or_(
                    col(Channel.public).is_(True),
                    col(Channel.user_id) == self._user.id,
                ),
            )

        return [main_channel.id, *self._session.exec(query).all()]

    def get_episodes(self) -> list[EpisodeResult]:
        """Get filtered, sorted episodes with channel IDs and latest watch data."""
        query = self._base_query()
        query = self._join_whitelist(query)
        query = self._join_show_last_watched(query)
        query = self._join_sequential_ranks(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._filter_by_plugin_visibility(query)
        query = self._filter_watched_episodes(query)
        query = self._filter_unwatched_episodes(query)
        query = self._filter_show_counts(query)
        query = self._filter_by_ranges(query)
        query = self._sort_episodes(query)
        query = self._apply_limit(query)

        # Dedupe by Episode.id: joining ChannelShow fans out when additional
        # channels are included. Preserving sort order, keep the first channel
        # seen for each episode.
        ordered_episodes: list[Episode] = []
        channel_by_episode: dict[UUID, UUID] = {}
        for episode, channel_id in self._session.exec(query).all():
            if episode.id in channel_by_episode:
                continue
            channel_by_episode[episode.id] = channel_id
            ordered_episodes.append(episode)

        watches = self._get_latest_watches(ordered_episodes)
        return [
            EpisodeResult(
                episode=episode,
                channel_id=channel_by_episode[episode.id],
                latest_watch=watches.get(episode.id),
            )
            for episode in ordered_episodes
        ]

    def _get_latest_watches(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, Watch]:
        """Get the latest watch for all episodes."""
        if not self._user or not episodes:
            return {}

        watches = self._session.exec(
            select(Watch)
            .where(
                col(Watch.episode_id).in_([episode.id for episode in episodes]),
                Watch.user_id == self._user.id,
            )
            .order_by(col(Watch.episode_id), desc(Watch.watch_date), desc(Watch.id))
            .distinct(col(Watch.episode_id)),
        ).all()

        return {watch.episode_id: watch for watch in watches}

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
            ChannelSeasonWhiteList,
            and_(
                ChannelSeasonWhiteList.channel_show_id == ChannelShow.id,
                ChannelSeasonWhiteList.season_id == Season.id,
            ),
        ).outerjoin(
            ChannelEpisodeWhiteList,
            and_(
                ChannelEpisodeWhiteList.channel_show_id == ChannelShow.id,
                ChannelEpisodeWhiteList.episode_id == Episode.id,
            ),
        )

    def _join_sequential_ranks(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        if any(
            key.field == "sequential" and key.model == "season"
            for key in self._channel_options.sort_by
        ):
            season_rank_sq = (
                select(
                    col(Season.id).label("season_id"),  # type: ignore[arg-type]
                    func.dense_rank()
                    .over(
                        partition_by=col(Season.show_id),
                        order_by=col(Season.season_number),
                    )
                    .label(RANK_COLUMN),
                )
                .where(col(Season.deleted_at).is_(None))
                .subquery(SEASON_RANK_SUBQUERY)
            )
            query = query.outerjoin(  # type: ignore[assignment]
                season_rank_sq,
                col(Season.id) == season_rank_sq.c.season_id,
            )

        if any(
            key.field == "sequential" and key.model == "episode"
            for key in self._channel_options.sort_by
        ):
            episode_rank_sq = (
                select(
                    col(Episode.id).label("episode_id"),  # type: ignore[arg-type]
                    func.dense_rank()
                    .over(
                        partition_by=col(Episode.season_id),
                        order_by=col(Episode.episode_number),
                    )
                    .label(RANK_COLUMN),
                )
                .where(col(Episode.deleted_at).is_(None))
                .subquery(EPISODE_RANK_SUBQUERY)
            )
            query = query.outerjoin(  # type: ignore[assignment]
                episode_rank_sq,
                col(Episode.id) == episode_rank_sq.c.episode_id,
            )

        return query

    def _join_show_last_watched(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        needs_last_watched = any(
            key.field == "last_watched" for key in self._channel_options.sort_by
        )
        if not needs_last_watched or not self._user:
            return query

        show_last_watched_subquery = (
            select(
                Season.show_id,
                func.max(Watch.watch_date).label(SHOW_LAST_WATCH_DATE_COLUMN),
            )
            .select_from(Watch)
            .join(Episode)
            .join(Season)
            .where(
                and_(
                    col(Watch.user_id) == self._user.id,
                    col(Episode.deleted_at).is_(None),
                ),
            )
            .group_by(col(Season.show_id))
            .subquery(SHOW_LAST_WATCHED_SUBQUERY)
        )

        return query.outerjoin(
            show_last_watched_subquery,
            col(Show.id) == show_last_watched_subquery.c.show_id,
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
        conditions = [col(Plugin.public).is_(True)]
        if self._user:
            conditions.append(col(Plugin.user_id) == self._user.id)  # type: ignore[arg-type]
        return (
            query.join(Source, col(Show.source_id) == Source.id)
            .join(Plugin, col(Source.plugin_id) == Plugin.id)
            .where(or_(*conditions))
        )

    @staticmethod
    def _channel_access_condition() -> ColumnElement[bool]:
        return or_(
            and_(
                col(ChannelShow.white_list_mode).is_(True),
                or_(
                    and_(
                        col(ChannelSeasonWhiteList.season_id).is_not(None),
                        col(ChannelEpisodeWhiteList.episode_id).is_(None),
                    ),
                    and_(
                        col(ChannelSeasonWhiteList.season_id).is_(None),
                        col(ChannelEpisodeWhiteList.episode_id).is_not(None),
                    ),
                ),
            ),
            and_(
                col(ChannelShow.white_list_mode).is_(False),
                or_(
                    and_(
                        col(ChannelSeasonWhiteList.season_id).is_(None),
                        col(ChannelEpisodeWhiteList.episode_id).is_(None),
                    ),
                    and_(
                        col(ChannelSeasonWhiteList.season_id).is_not(None),
                        col(ChannelEpisodeWhiteList.episode_id).is_not(None),
                    ),
                ),
            ),
        )

    def _filter_episodes_by_channels(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return query.where(
            col(ChannelShow.channel_id).in_(self._channel_ids),
        ).where(self._channel_access_condition())

    def _verified_watches_subquery(self) -> SelectOfScalar[UUID]:
        user = self._require_user()
        return select(Watch.episode_id).where(
            and_(
                Watch.user_id == user.id,
                col(Watch.verified).is_(True),
            ),
        )

    def _hide_watched_condition(self) -> ColumnElement[bool] | None:
        if not (self._user and self._channel_options.hide_watched):
            return None
        watched_subquery = self._verified_watches_subquery()
        absolute_date = self._channel_options.maximum_watch_date_absolute
        relative_date = self._channel_options.maximum_watch_date_relative
        if max_watch_date := self._parse_date_filter(absolute_date, relative_date):
            watched_subquery = watched_subquery.where(
                Watch.watch_date > max_watch_date,
            )
        return col(Episode.id).not_in(watched_subquery)

    def _hide_unwatched_condition(self) -> ColumnElement[bool] | None:
        if not (self._user and self._channel_options.hide_unwatched):
            return None
        return col(Episode.id).in_(self._verified_watches_subquery())

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

    def _started_shows_subquery(self) -> SelectOfScalar[UUID]:
        user = self._require_user()
        return (
            select(Show.id)
            .join(Season, col(Show.id) == Season.show_id)
            .join(Episode, col(Season.id) == Episode.season_id)
            .join(
                Watch,
                and_(
                    Watch.episode_id == Episode.id,
                    Watch.user_id == user.id,
                ),
            )
            .where(col(Watch.verified).is_(True))
            .distinct()
        )

    def _filter_show_counts(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Filter shows by total, started, and new counts."""
        if not self._user:
            return query

        if (
            self._channel_options.total_shows_count is None
            and self._channel_options.started_shows_count is None
            and self._channel_options.new_shows_count is None
        ):
            return query
        available_show_ids = self._reachable_show_ids()
        started_show_ids = set(
            self._session.exec(self._started_shows_subquery()).all(),
        )
        available_started = available_show_ids & started_show_ids
        available_new = available_show_ids - started_show_ids

        selected = _select_show_subset(
            started_available=available_started,
            new_available=available_new,
            total=self._channel_options.total_shows_count,
            started_count=self._channel_options.started_shows_count,
            new_count=self._channel_options.new_shows_count,
            random_seed=self._channel_options.random_seed,
        )
        return query.where(col(Show.id).in_(selected))

    def _reachable_show_ids(self) -> set[UUID]:
        """Show IDs with at least one episode that survives the episode filters.

        Mirrors the channel-access predicate (whitelist/blacklist + channel
        scope), the hide_watched/hide_unwatched predicates, and the
        air/release/duration range filters so that shows whose only surviving
        episodes would be filtered out do not occupy a selection slot in
        ``_filter_show_counts``.
        """
        query = (
            select(Show.id)
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
            .outerjoin(
                ChannelSeasonWhiteList,
                and_(
                    ChannelSeasonWhiteList.channel_show_id == ChannelShow.id,
                    ChannelSeasonWhiteList.season_id == Season.id,
                ),
            )
            .outerjoin(
                ChannelEpisodeWhiteList,
                and_(
                    ChannelEpisodeWhiteList.channel_show_id == ChannelShow.id,
                    ChannelEpisodeWhiteList.episode_id == Episode.id,
                ),
            )
            .where(col(Episode.deleted_at).is_(None))
            .where(col(ChannelShow.channel_id).in_(self._channel_ids))
            .where(self._channel_access_condition())
            .distinct()
        )
        if (hide_watched := self._hide_watched_condition()) is not None:
            query = query.where(hide_watched)
        if (hide_unwatched := self._hide_unwatched_condition()) is not None:
            query = query.where(hide_unwatched)
        for condition in self._episode_range_conditions():
            query = query.where(condition)
        return set(self._session.exec(query).all())

    def _episode_range_conditions(self) -> list[ColumnElement[bool]]:
        """WHERE predicates for configured air-date / release-date / duration ranges.

        Each range emits up to two predicates (min and max). Null values in
        the column are allowed through so an episode with a missing
        air_date/release_date/duration is never excluded purely by the range.
        """
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

    def _apply_limit(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        user_limit = self._channel_options.limit
        limit = min(user_limit or MAX_EPISODES_RETURNED, MAX_EPISODES_RETURNED)
        return query.limit(limit)

    def _sort_episodes(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        if not self._channel_options.sort_by:
            return query
        expressions = self._sort_expressions
        labeled_values: list[ColumnElement[Any]] = [
            expressions.expression(sort_key).label(f"sv_{index}")
            for index, sort_key in enumerate(self._channel_options.sort_by)
        ]
        labeled_values.append(Season.show_id.label("show_id"))  # type: ignore[arg-type]
        inner = query.add_columns(*labeled_values).subquery()

        raws = [
            getattr(inner.c, f"sv_{i}")
            for i in range(len(self._channel_options.sort_by))
        ]
        directeds = [
            expressions.apply_direction(raws[i], key)
            for i, key in enumerate(self._channel_options.sort_by)
        ]

        order_by: list[UnaryExpression[Any] | ColumnElement[Any]] = []
        for index, sort_key in enumerate(self._channel_options.sort_by):
            if sort_key.order == "sequential":
                order_by.append(directeds[index])
                continue

            row_num = func.row_number().over(
                partition_by=raws[: index + 1],
                order_by=directeds[index + 1 :] or [directeds[index]],
            )
            partition_order = (
                expressions.random_hash(raws[index])
                if sort_key.order == "randomize"
                else directeds[index]
            )
            order_by.extend([row_num, partition_order])

        order_by.extend([inner.c.show_id, inner.c.id])

        outer: Select[tuple[Episode, UUID]] = select(  # type: ignore[assignment]
            aliased(Episode, inner),
            inner.c.channel_id,
        )
        return outer.order_by(*order_by)
