# TODO: Validate
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
from app.channels.schemas import ChannelMediaFilter, SortKeyInput
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000


@dataclass
class EpisodeResult:
    episode: Episode
    channel_id: UUID
    latest_watch: Watch | None = None


class EpisodeQueryBuilder:
    def __init__(
        self,
        session: SessionDep,
        channel: Channel,
        media_filter: ChannelMediaFilter,
        user: CurrentUser | None = None,
    ) -> None:
        self._session = session
        self._user = user
        self._media_filter = media_filter
        self._sort_keys = self._filter_sort_keys(media_filter)
        self._channel_ids: list[UUID] = []
        self._compile_channel_ids(channel)

    def _filter_sort_keys(
        self,
        media_filter: ChannelMediaFilter,
    ) -> list[SortKeyInput]:
        """Filter out sort keys that require a user when none is authenticated.

        This filter intentionally does not raise an error so a user can share a link to
        a channel without the other user having to make an account."""
        return [
            sort_key
            for sort_key in media_filter.sort_by
            if sort_key.field != "last_watched" or self._user is not None
        ]

    def _compile_channel_ids(self, main_channel: Channel) -> None:
        """Compile a list of channels that the user has access to."""
        additional_ids = self._media_filter.additional_channels
        if not additional_ids:
            self._channel_ids = [main_channel.id]
            return

        query = select(Channel.id).where(col(Channel.id).in_(additional_ids))
        if not (self._user and self._user.is_superuser):
            if self._user:
                query = query.where(
                    or_(
                        col(Channel.public).is_(True),
                        col(Channel.user_id) == self._user.id,
                    ),
                )
            else:
                query = query.where(col(Channel.public).is_(True))

        readable_ids = self._session.exec(query).all()
        self._channel_ids = [main_channel.id, *readable_ids]

    def get_episodes(self) -> list[EpisodeResult]:
        """Get filtered, sorted episodes with channel IDs and latest watch data."""
        query = self._base_query()
        query = self._join_whitelist_tables(query)
        query = self._join_show_last_watched(query)
        query = self._join_sequential_ranks(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._filter_by_plugin_visibility(query)
        query = self._filter_watched_episodes(query)
        query = self._filter_unwatched_episodes(query)
        query = self._filter_only_started_shows(query)
        query = self._filter_only_new_shows(query)
        query = self._filter_by_air_date(query)
        query = self._filter_by_release_date(query)
        query = self._filter_by_duration(query)
        query = self._sort_episodes(query)
        query = self._apply_limit(query)
        rows = self._session.exec(query).all()

        episodes = [row[0] for row in rows]
        channels = self._get_episode_channels(episodes)
        watches = self._get_latest_watches(episodes)

        return [
            EpisodeResult(
                episode=episode,
                channel_id=channels[episode.id],
                latest_watch=watches.get(episode.id),
            )
            for episode in episodes
            if episode.id in channels
        ]

    def _get_episode_channels(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, UUID]:
        """Get the channel ID for each episode."""
        query = (
            select(Episode.id, ChannelShow.channel_id)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
        )
        query = self._join_whitelist_tables(query)
        query = query.where(col(Episode.id).in_([ep.id for ep in episodes]))
        query = query.where(col(ChannelShow.channel_id).in_(self._channel_ids))
        query = self._filter_episodes_by_channels(query)
        results = self._session.exec(query).all()
        return dict(results)

    def _get_latest_watches(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, Watch]:
        """Get the latest watch for each episode."""
        if not self._user or not episodes:
            return {}

        max_dates = (
            select(
                Watch.episode_id,
                func.max(Watch.watch_date).label("max_date"),
            )
            .where(
                and_(
                    col(Watch.episode_id).in_(
                        [episode.id for episode in episodes],
                    ),
                    Watch.user_id == self._user.id,
                ),
            )
            .group_by(col(Watch.episode_id))
            .subquery()
        )

        watches = self._session.exec(
            select(Watch)
            .join(
                max_dates,
                and_(
                    Watch.episode_id == max_dates.c.episode_id,
                    Watch.watch_date == max_dates.c.max_date,
                ),
            )
            .where(Watch.user_id == self._user.id),
        ).all()

        return {watch.episode_id: watch for watch in watches}

    def _base_query(self) -> Select[tuple[Episode, Any]]:
        if not self._sort_keys:
            self._sort_keys.append(
                SortKeyInput(
                    model="episode",
                    field="random",
                    direction="ascending",
                ),
            )

        sort_expression = self._sort_value_expr(self._sort_keys[-1])

        return (
            select(Episode, sort_expression.label("primary_sort_value"))
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
        )

    def _join_whitelist_tables[
        T: Select[tuple[UUID, UUID]] | Select[tuple[Episode, Any]],
    ](
        self,
        query: T,
    ) -> T:
        # return-value - MyPy doesn't understand this but Pylance does.
        return query.outerjoin(  # type: ignore[return-value]
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
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        """Join precomputed dense_rank subqueries for any sequential sort keys.

        Computes rank in a single window-function pass over the unfiltered
        (sans-deleted) base table, so ``hide_watched`` and other outer
        filters don't shift ranks the way they would if we ranked the
        post-filter rows. Replaces the per-row correlated subqueries that
        previously dominated the query plan.
        """
        needs_episode_rank = any(
            key.field == "sequential" and key.model == "episode"
            for key in self._sort_keys
        )
        needs_season_rank = any(
            key.field == "sequential" and key.model == "season"
            for key in self._sort_keys
        )

        if needs_season_rank:
            season_rank_sq = (
                select(
                    col(Season.id).label("season_id"),  # type: ignore[arg-type]
                    func.dense_rank()
                    .over(
                        partition_by=col(Season.show_id),
                        order_by=col(Season.season_number),
                    )
                    .label("rank"),
                )
                .where(col(Season.deleted_at).is_(None))
                .subquery("season_rank")
            )
            query = query.outerjoin(  # type: ignore[assignment]
                season_rank_sq,
                col(Season.id) == season_rank_sq.c.season_id,
            )

        if needs_episode_rank:
            episode_rank_sq = (
                select(
                    col(Episode.id).label("episode_id"),  # type: ignore[arg-type]
                    func.dense_rank()
                    .over(
                        partition_by=col(Episode.season_id),
                        order_by=col(Episode.episode_number),
                    )
                    .label("rank"),
                )
                .where(col(Episode.deleted_at).is_(None))
                .subquery("episode_rank")
            )
            query = query.outerjoin(  # type: ignore[assignment]
                episode_rank_sq,
                col(Episode.id) == episode_rank_sq.c.episode_id,
            )

        return query

    def _join_show_last_watched(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        needs_last_watched = any(key.field == "last_watched" for key in self._sort_keys)
        if not needs_last_watched or not self._user:
            return query

        show_last_watched_subquery = (
            select(
                Season.show_id,
                func.max(Watch.watch_date).label("show_last_watch_date"),
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
            .subquery("show_last_watched")
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
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return query.where(col(Episode.deleted_at).is_(None))

    def _filter_by_plugin_visibility(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        """Filter out episodes from private plugins the viewer doesn't own."""
        conditions = [col(Plugin.public).is_(True)]
        if self._user:
            conditions.append(col(Plugin.user_id) == self._user.id)  # type: ignore[arg-type]
        return (
            query.join(Source, col(Show.source_id) == Source.id)
            .join(Plugin, col(Source.plugin_id) == Plugin.id)
            .where(or_(*conditions))
        )

    def _filter_episodes_by_channels[
        T: Select[tuple[Episode, Any]] | Select[tuple[UUID, UUID]],
    ](
        self,
        query: T,
    ) -> T:
        # return-value - MyPy doesn't understand this but Pylance does.
        query = query.where(col(ChannelShow.channel_id).in_(self._channel_ids))  # type: ignore[assignment]
        # return-value - MyPy doesn't understand this but Pylance does.
        return query.where(  # type: ignore[return-value]
            or_(
                and_(
                    col(ChannelShow.white_list_mode).is_(True),
                    or_(
                        # Season is whitelisted and episode is not individually excluded
                        and_(
                            col(ChannelSeasonWhiteList.season_id).is_not(None),
                            col(ChannelEpisodeWhiteList.episode_id).is_(None),
                        ),
                        # Episode is individually whitelisted (no season whitelist)
                        and_(
                            col(ChannelSeasonWhiteList.season_id).is_(None),
                            col(ChannelEpisodeWhiteList.episode_id).is_not(None),
                        ),
                    ),
                ),
                and_(
                    col(ChannelShow.white_list_mode).is_(False),
                    or_(
                        # Not blacklisted at all
                        and_(
                            col(ChannelSeasonWhiteList.season_id).is_(None),
                            col(ChannelEpisodeWhiteList.episode_id).is_(None),
                        ),
                        # Season is blacklisted but episode is individually un-blacklisted
                        and_(
                            col(ChannelSeasonWhiteList.season_id).is_not(None),
                            col(ChannelEpisodeWhiteList.episode_id).is_not(None),
                        ),
                    ),
                ),
            ),
        )

    def _verified_watches_subquery(self) -> SelectOfScalar[UUID]:
        """Subquery selecting episode IDs with verified watches for the current user."""
        return select(Watch.episode_id).where(
            and_(
                Watch.user_id == self._user.id,  # type: ignore[union-attr]
                col(Watch.verified).is_(True),
            ),
        )

    def _filter_watched_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.hide_watched):
            return query

        watched_subquery = self._verified_watches_subquery()

        absolute_date = self._media_filter.maximum_watch_date_absolute
        relative_date = self._media_filter.maximum_watch_date_relative
        if max_watch_date := self._parse_date_filter(absolute_date, relative_date):
            watched_subquery = watched_subquery.where(
                Watch.watch_date > max_watch_date,
            )

        return query.where(col(Episode.id).not_in(watched_subquery))

    def _filter_unwatched_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.hide_unwatched):
            return query
        return query.where(col(Episode.id).in_(self._verified_watches_subquery()))

    def _started_shows_subquery(self) -> SelectOfScalar[UUID]:
        if not self._user:
            msg = "Started shows subquery requires a valid user"
            raise ValueError(msg)

        return (
            select(Show.id)
            .join(Season, col(Show.id) == Season.show_id)
            .join(Episode, col(Season.id) == Episode.season_id)
            .join(
                Watch,
                and_(
                    Watch.episode_id == Episode.id,
                    Watch.user_id == self._user.id,
                ),
            )
            .where(col(Watch.verified).is_(True))
            .distinct()
        )

    def _filter_only_started_shows(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.only_started_shows):
            return query
        return query.where(col(Show.id).in_(self._started_shows_subquery()))

    def _filter_only_new_shows(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not (self._user and self._media_filter.only_new_shows):
            return query
        return query.where(col(Show.id).not_in(self._started_shows_subquery()))

    def _apply_nullable_range_filter(
        self,
        query: Select[tuple[Episode, Any]],
        column: ColumnElement[Any] | Mapped[Any],
        min_value: datetime | int | None,
        max_value: datetime | int | None,
    ) -> Select[tuple[Episode, Any]]:
        """Apply a min/max range filter that allows NULL values through."""
        if min_value is not None:
            query = query.where(or_(column >= min_value, column.is_(None)))
        if max_value is not None:
            query = query.where(or_(column <= max_value, column.is_(None)))
        return query

    def _filter_by_air_date(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return self._apply_nullable_range_filter(
            query,
            col(Episode.air_date),
            self._parse_date_filter(
                self._media_filter.minimum_air_date_absolute,
                self._media_filter.minimum_air_date_relative,
            ),
            self._parse_date_filter(
                self._media_filter.maximum_air_date_absolute,
                self._media_filter.maximum_air_date_relative,
            ),
        )

    def _filter_by_release_date(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return self._apply_nullable_range_filter(
            query,
            col(Episode.release_date),
            self._parse_date_filter(
                self._media_filter.minimum_release_date_absolute,
                self._media_filter.minimum_release_date_relative,
            ),
            self._parse_date_filter(
                self._media_filter.maximum_release_date_absolute,
                self._media_filter.maximum_release_date_relative,
            ),
        )

    def _filter_by_duration(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        return self._apply_nullable_range_filter(
            query,
            col(Episode.duration),
            self._media_filter.minimum_duration,
            self._media_filter.maximum_duration,
        )

    def _apply_limit(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        user_limit = self._media_filter.limit
        limit = (
            min(user_limit, MAX_EPISODES_RETURNED)
            if user_limit is not None
            else MAX_EPISODES_RETURNED
        )
        return query.limit(limit)

    def _sort_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        """Build ORDER BY from sort keys.

        Sort values are materialized in an inner subquery so window-function
        values (aggregates, episode_count, etc.) can be referenced inside
        outer window PARTITION BY clauses without violating Postgres's
        nested-window restriction.
        """
        labeled_values: list[ColumnElement[Any]] = [
            self._sort_value_expr(sort_key).label(f"sv_{index}")
            for index, sort_key in enumerate(self._sort_keys)
        ]
        # show_id is materialized so it can serve as the primary deterministic
        # tiebreak below, keeping same-show episodes adjacent when every
        # user-specified key ties.
        labeled_values.append(Season.show_id.label("show_id"))  # type: ignore[arg-type]
        inner = query.add_columns(*labeled_values).subquery()

        raws = [getattr(inner.c, f"sv_{i}") for i in range(len(self._sort_keys))]
        directeds = [
            self._apply_direction(raws[i], key) for i, key in enumerate(self._sort_keys)
        ]

        order_by: list[UnaryExpression[Any] | ColumnElement[Any]] = []
        for index, sort_key in enumerate(self._sort_keys):
            if sort_key.order == "sequential":
                order_by.append(directeds[index])
                continue

            # interleave / randomize: partition by this value and spread rows
            # with row_number. Inner ORDER BY uses the subsequent sort keys so
            # row_num=1 picks each partition's first sequential row, row_num=2
            # the second, etc. randomize shuffles the partition order.
            row_num = func.row_number().over(
                partition_by=raws[: index + 1],
                order_by=directeds[index + 1 :] or [directeds[index]],
            )
            partition_order = (
                self._random_hash(raws[index])
                if sort_key.order == "randomize"
                else directeds[index]
            )
            order_by.extend([row_num, partition_order])

        # Final deterministic tiebreaks.
        order_by.extend([inner.c.show_id, inner.c.id])

        outer: Select[tuple[Episode, Any]] = select(  # type: ignore[assignment]
            aliased(Episode, inner),
            inner.c.primary_sort_value,
        )
        return outer.order_by(*order_by)

    @staticmethod
    def _apply_direction(
        expr: ColumnElement[Any],
        sort_key: SortKeyInput,
    ) -> UnaryExpression[Any] | ColumnElement[Any]:
        """Add direction and null-handling to a raw sort value."""
        directed: UnaryExpression[Any] | ColumnElement[Any] = (
            desc(expr) if sort_key.direction == "descending" else expr
        )
        # Never-watched episodes (NULL last_watched) should appear first when
        # ascending so unwatched content surfaces before rewatches.
        if sort_key.field == "last_watched" and sort_key.direction == "ascending":
            return directed.nulls_first()
        return directed.nulls_last()

    def _random_hash(self, expr: ColumnElement[Any]) -> ColumnElement[Any]:
        """Stable pseudo-random ordering keyed by ``expr`` and the user seed."""
        return func.hashtext(
            func.concat(
                func.cast(expr, String),
                str(self._media_filter.random_seed),
            ),
        )

    def _sort_value_expr(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        """Return the SQL expression for a sort key's raw value."""
        if sort_key.aggregation and sort_key.model == "episode":
            return self._aggregate_episode_expr(sort_key)
        return self._value_expr(sort_key)

    def _value_expr(self, sort_key: SortKeyInput) -> ColumnElement[Any]:  # noqa: PLR0911
        """SQL expression for a non-aggregate sort key."""
        field = sort_key.field

        if field == "random":
            random_ids: dict[str, Mapped[UUID]] = {
                "episode": Episode.id,  # type: ignore[dict-item]
                "season": Season.id,  # type: ignore[dict-item]
                "show": Show.id,  # type: ignore[dict-item]
            }
            return self._random_hash(random_ids[sort_key.model])
        if field == "sequential":
            return self._sequential_rank(sort_key.model)
        if field == "recently_aired":
            return self._recently_aired_expr(sort_key)
        if field == "last_watched":
            return literal_column("show_last_watched.show_last_watch_date")
        if field == "episode_count":
            return func.count(Episode.id).over(partition_by=col(Show.id))  # type: ignore[arg-type]
        if field == "started" and sort_key.model == "show":
            return self._started_show_expr()

        # no-any-return - Validated to be a ColumnElement.
        return getattr(sort_key.model_class, field)  # type: ignore[no-any-return]

    def _aggregate_episode_expr(
        self,
        sort_key: SortKeyInput,
    ) -> ColumnElement[Any]:
        """Aggregate an episode field per show (e.g. max air_date per show)."""
        if sort_key.field == "last_watched":
            return literal_column("show_last_watched.show_last_watch_date")

        if sort_key.field == "random":
            episode_field: ColumnElement[Any] = self._random_hash(Show.id)  # type: ignore[arg-type]
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
            return literal_column("episode_rank.rank")
        if model == "season":
            return literal_column("season_rank.rank")
        msg = f"sequential is not supported for model '{model}'"
        raise ValueError(msg)

    @staticmethod
    def _recently_aired_expr(sort_key: SortKeyInput) -> ColumnElement[Any]:
        """1 if the episode aired on/after the cutoff, else 0."""
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
        """1 if the show has any verified watch by the current user, else 0."""
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
