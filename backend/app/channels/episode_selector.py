from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import String, case, literal_column
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.expression import ColumnElement, UnaryExpression
from sqlmodel import and_, col, desc, func, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels.dependencies import get_readable_channels
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
        additional_channels = get_readable_channels(
            self._session,
            self._user,
            self._media_filter.additional_channels,
        )
        self._channel_ids = [main_channel.id, *(x.id for x in additional_channels)]

    def get_episodes(self) -> list[EpisodeResult]:
        """Get filtered, sorted episodes with channel IDs and latest watch data."""
        query = self._base_query()
        query = self._join_whitelist_tables(query)
        query = self._join_show_last_watched(query)
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
        channel_map = self._get_episode_channels(episodes)
        watch_map = self._get_latest_watches(episodes)

        return [
            EpisodeResult(
                episode=episode,
                channel_id=channel_map[episode.id],
                latest_watch=watch_map.get(episode.id),
            )
            for episode in episodes
            if episode.id in channel_map
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
                    mode="normal",
                ),
            )

        sort_expression = self._get_sorter(self._sort_keys[-1])

        query = (
            select(Episode, sort_expression.label("primary_sort_value"))
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(ChannelShow)
        )
        return query.limit(MAX_EPISODES_RETURNED)

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
            conditions.append(col(Plugin.user_id) == self._user.id)
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
                        col(ChannelSeasonWhiteList.season_id).is_not(None),
                        col(ChannelEpisodeWhiteList.episode_id).is_not(None),
                    ),
                ),
                and_(
                    col(ChannelShow.white_list_mode).is_(False),
                    col(ChannelSeasonWhiteList.season_id).is_(None),
                    col(ChannelEpisodeWhiteList.episode_id).is_(None),
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
        if self._media_filter.limit is not None:
            return query.limit(self._media_filter.limit)
        return query

    @property
    def _has_interleave(self) -> bool:
        return any(
            sort_key.mode in ("interleave_sequential", "interleave_random")
            for sort_key in self._sort_keys
        )

    @property
    def _interleave_is_random(self) -> bool:
        return any(sort_key.mode == "interleave_random" for sort_key in self._sort_keys)

    def _collect_sort_expressions(
        self,
        *,
        exclude_show_group: bool = False,
    ) -> list[UnaryExpression[Any] | ColumnElement[Any]]:
        """Collect sort expressions from configured sort keys.

        Args:
            exclude_show_group: If True, skip show_group sort keys (used for
                window function partitioning to avoid nested window functions).
        """
        sort_expressions: list[UnaryExpression[Any] | ColumnElement[Any]] = []
        for sort_key in reversed(self._sort_keys):
            if exclude_show_group and sort_key.mode == "show_group":
                continue
            sort_expressions.append(self._sql_sort_expression(sort_key))
        return sort_expressions

    def _sort_episodes(
        self,
        query: Select[tuple[Episode, Any]],
    ) -> Select[tuple[Episode, Any]]:
        if not self._has_interleave:
            return query.order_by(*self._collect_sort_expressions())

        sort_expressions = self._collect_sort_expressions()
        remaining_sorts = sort_expressions[1:]

        last_sort_key = self._sort_keys[-1]
        if last_sort_key.mode == "show_group":
            partition_by = col(Show.id)
        else:
            partition_by = self._get_sorter(last_sort_key)
        interleave_partition = func.row_number().over(
            partition_by=partition_by,
            order_by=self._collect_sort_expressions(exclude_show_group=True),
        )

        if self._interleave_is_random:
            show_random = func.hashtext(
                func.concat(
                    func.cast(Show.id, String),
                    str(self._media_filter.random_seed),
                ),
            )
            return query.order_by(
                interleave_partition,
                show_random,
                *remaining_sorts,
            )

        return query.order_by(interleave_partition, *remaining_sorts)

    def _get_sorter(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        """Route a sort key to the appropriate SQL expression builder."""
        if sort_key.mode == "show_group" and sort_key.model == "episode":
            return self._sql_sort_by_show_episodes_expression(sort_key)
        return self._sql_sort_by_value_expression(sort_key)

    def _sql_sort_expression(
        self,
        sort_key: SortKeyInput,
    ) -> UnaryExpression[Any] | ColumnElement[Any]:
        sorter = self._get_sorter(sort_key)

        if sort_key.direction == "descending":
            sorter = desc(sorter)

        # Last watched with ascending should have nulls first because never watched
        # episodes should appear first.
        if sort_key.field == "last_watched" and sort_key.direction == "ascending":
            sorter = sorter.nulls_first()
        else:
            sorter = sorter.nulls_last()

        return sorter

    def _sql_sort_by_value_expression(
        self,
        sort_key: SortKeyInput,
    ) -> ColumnElement[Any]:
        """Get SQL expression for a value-based sort."""
        if sort_key.field == "random":
            return func.hashtext(
                func.concat(
                    func.cast(Episode.id, String),
                    str(self._media_filter.random_seed),
                ),
            )
        if sort_key.field == "recently_aired":
            if sort_key.recently_aired_date:
                return self._recently_airing_sort_expression_absolute(
                    sort_key.recently_aired_date,
                )
            return self._recently_airing_sort_expression(sort_key.days or 7)
        if sort_key.field == "last_watched":
            return literal_column("show_last_watched.show_last_watch_date")
        if sort_key.field == "episode_count":
            return func.count(Episode.id).over(partition_by=col(Show.id))
        if sort_key.model == "show" and sort_key.field == "started":
            return self._started_show_sort_expression()

        # no-any-return - Validated to be a ColumnElement.
        return getattr(sort_key.model_class, sort_key.field)  # type: ignore[no-any-return]

    def _sql_sort_by_show_episodes_expression(
        self,
        sort_key: SortKeyInput,
    ) -> ColumnElement[Any]:
        """Get aggregate window function for show-grouped episode sorting."""
        if sort_key.field == "last_watched":
            return literal_column("show_last_watched.show_last_watch_date")

        if sort_key.field == "random":
            salt = str(self._media_filter.random_seed)
            episode_field = func.hashtext(
                func.concat(func.cast(Show.id, String), salt),
            )
        elif sort_key.field == "recently_aired":
            if sort_key.recently_aired_date:
                episode_field = self._recently_airing_sort_expression_absolute(
                    sort_key.recently_aired_date,
                )
            else:
                episode_field = self._recently_airing_sort_expression(
                    sort_key.days or 7,
                )
        elif sort_key.field == "episode_count":
            episode_field = Episode.id
        else:
            episode_field = getattr(Episode, sort_key.field)

        agg_funcs: dict[str, Any] = {
            "sum": func.sum,
            "avg": func.avg,
            "count": func.count,
            "max": func.max,
            "min": func.min,
            "first_value": func.first_value,
        }
        agg_func = agg_funcs.get(sort_key.aggregation)
        if agg_func is None:
            msg = f"Unsupported aggregation '{sort_key.aggregation}'"
            raise ValueError(msg)

        return agg_func(episode_field).over(partition_by=col(Show.id))

    def _recently_airing_sort_expression(self, days: int) -> ColumnElement[Any]:
        cutoff = tz_datetime.now() - timedelta(days=days)
        return self._recently_airing_sort_expression_absolute(cutoff)

    @staticmethod
    def _recently_airing_sort_expression_absolute(
        cutoff: datetime,
    ) -> ColumnElement[Any]:
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

    def _started_show_sort_expression(self) -> ColumnElement[Any]:
        if not self._user:
            return literal_column("0")
        started_query = (
            select(Watch.id)
            .join(Episode, Watch.episode_id == Episode.id)
            .join(Season, Episode.season_id == Season.id)
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
