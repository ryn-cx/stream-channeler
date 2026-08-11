# TODO: Validate
"""Reading the episodes a channel offers, in the order it offers them."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, distinct
from sqlalchemy.orm import Mapped, aliased
from sqlalchemy.sql.expression import ColumnElement, Subquery, UnaryExpression
from sqlmodel import and_, col, func, or_, select
from sqlmodel.sql.expression import Select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channel_orders.models import ChannelOrder
from app.channels.channel_scope import (
    channel_attribution,
    child_channel_ids,
    resolve_channel_ids,
)
from app.channels.episode_selector.show_counts import limit_shows
from app.channels.episode_selector.sorting import SortExpressionBuilder
from app.channels.episode_selector.source_dedup import source_dedup_config
from app.channels.episode_selector.tmdb_columns import TMDBFallbackColumns
from app.channels.episode_selector.visibility import (
    blacklisted_on_channels_condition,
    channel_access_condition,
)
from app.channels.episode_selector.watch_filters import (
    LAST_WATCHED_COLUMNS,
    hide_partially_watched_condition,
    hide_unwatched_condition,
    hide_watched_condition,
    join_last_watched,
    latest_watch_by_identifier,
)
from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelSavedEpisodeOrder,
    ChannelSeasonFilter,
    ChannelShow,
    ChannelSourceFilter,
)
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.media.tmdb_fallback import TMDB_PLUGIN_KEY
from app.models import Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000


# TODO: Validate
@dataclass
class EpisodeResult:
    episode: Episode
    channel_id: UUID
    channel_ids: list[UUID]
    latest_watch: Watch | None = None


# TODO: Validate
class EpisodeQueryBuilder:
    # TODO: Validate
    def __init__(
        self,
        session: SessionDep,
        channel: Channel,
        channel_options: ChannelOptions,
        user: CurrentUser | None = None,
    ) -> None:
        self._session = session
        self._channel = channel
        self._user = user
        self._set_channel_options(channel_options)

        self._channel_ids = self._fetch_channel_ids()

        self._source_config = source_dedup_config(session, self._user)
        self._holds_copied_titles = self._fetch_holds_copied_titles()

        self._tmdb_fallbacks = TMDBFallbackColumns()
        self._sort_expressions = SortExpressionBuilder(
            random_seed=self._channel_options.random_seed,
            user=self._user,
            fallbacks=self._tmdb_fallbacks,
            # Only a read that orders by the channel an episode comes from has to
            # work out which channel that is.
            channel_attribution=(
                channel_attribution(session, self._user, self._channel)
                if any(key.model == "channel" for key in self._channel_options.sort_by)
                else {}
            ),
        )

    # TODO: Validate
    def _set_channel_options(self, channel_options: ChannelOptions) -> None:
        self._channel_options = channel_options.model_copy(deep=True)
        self._fetch_channel_order_preset()
        self._filter_channel_options()

    # TODO: Validate
    def _fetch_channel_order_preset(self) -> None:
        """Return the channel's options with a saved `ChannelOrder` preset."""
        if self._channel_options.order_preset_id:
            query = select(ChannelOrder).where(
                ChannelOrder.id == self._channel_options.order_preset_id,
            )
            if order := self._session.exec(query).first():
                self._channel_options = ChannelOptions.model_validate_json(order.config)

    # TODO: Validate
    def _filter_channel_options(
        self,
    ) -> None:
        """Removes channel options that require the user to be logged in if they are not logged in."""
        if not self._user:
            self._channel_options.sort_by = [
                sort_key
                for sort_key in self._channel_options.sort_by
                if sort_key.field not in LAST_WATCHED_COLUMNS
            ]
            self._channel_options.hide_watched = False
            self._channel_options.hide_unwatched = False
            self._channel_options.hide_partially_watched = False
            self._channel_options.maximum_watch_date_absolute = None
            self._channel_options.maximum_watch_date_relative = None
            self._channel_options.total_shows_count = None
            self._channel_options.started_shows_count = None
            self._channel_options.new_shows_count = None

    # TODO: Validate
    def _fetch_holds_copied_titles(self) -> bool:
        """Whether the channel can be holding a title as more than one copy.

        Collapsing the copies of an episode means reading every episode the channel
        offers before any of them can be returned, since a copy the row limit never
        reached may be the one that wins. A channel with no title to collapse skips
        the ranking and lets the limit stop it early instead.

        Asked of the titles rather than of their episodes, which is what keeps it
        cheap: a channel holds tens of titles where it offers thousands of episodes.
        One website carrying a title twice counts as much as two websites carrying
        it once, since either leaves an episode with a copy to be ranked against.
        """
        totals = (
            select(
                func.count(distinct(col(Show.source_id))),
                func.count(distinct(col(Show.id))),
                func.count(distinct(col(Show.show_identifier))),
            )
            .select_from(ChannelShow)
            .join(Show, col(ChannelShow.show_identifier) == col(Show.show_identifier))
            .where(col(ChannelShow.channel_id).in_(self._channel_ids))
            .where(col(ChannelShow.is_blacklist_only).is_(False))
            .where(col(Show.deleted_at).is_(None))
        )
        sources, shows, titles = self._session.exec(totals).one()  # type: ignore[misc]
        return sources > 1 or shows > titles

    # TODO: Validate
    def _fetch_channel_ids(self) -> set[UUID]:
        return resolve_channel_ids(
            self._session,
            self._user,
            self._channel,
            child_channel_ids(self._channel),
        )

    # TODO: Validate
    def get_episodes(self) -> list[EpisodeResult]:
        """Get filtered, sorted episodes with channel IDs and latest watch data."""
        query = self._base_query()
        query = self._join_whitelist(query)
        query = self._join_last_watched(query)
        query = self._join_saved_order(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._apply_channel_specific_blacklist(query)
        query = self._filter_by_plugin_visibility(query)
        query = self._filter_metadata_plugins(query)
        query = self._filter_disabled_sources(query)
        query = self._filter_by_watch_state(query)
        query = self._filter_by_ranges(query)
        query = self._sort_and_deduplicate(query)
        query = self._apply_limit(query)

        ordered_episodes: list[Episode] = []
        channels_by_identifier: dict[str, list[UUID]] = {}
        for episode, channel_id in self._session.exec(query).all():
            identifier = episode.episode_identifier
            if identifier not in channels_by_identifier:
                channels_by_identifier[identifier] = []
                ordered_episodes.append(episode)
            if channel_id not in channels_by_identifier[identifier]:
                channels_by_identifier[identifier].append(channel_id)

        ordered_episodes = limit_shows(
            self._session,
            self._user,
            ordered_episodes,
            self._channel_options,
        )
        ordered_episodes = ordered_episodes[: self._result_limit()]

        watches = (
            latest_watch_by_identifier(
                self._session,
                self._user,
                ordered_episodes,
            )
            if self._user
            else {}
        )
        return [
            EpisodeResult(
                episode=episode,
                channel_id=channels_by_identifier[episode.episode_identifier][0],
                channel_ids=channels_by_identifier[episode.episode_identifier],
                latest_watch=watches.get(episode.episode_identifier),
            )
            for episode in ordered_episodes
        ]

    # TODO: Validate
    def _base_query(self) -> Select[tuple[Episode, UUID]]:
        # A channel holds titles rather than one website's copy of them, so every
        # copy of a title the channel holds is joined to the same `ChannelShow`.
        return (
            select(Episode, ChannelShow.channel_id)  # type: ignore[call-overload]
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(
                ChannelShow,
                col(ChannelShow.show_identifier) == col(Show.show_identifier),
            )
        )

    # TODO: Validate
    def _join_whitelist(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return (
            query.outerjoin(
                ChannelSourceFilter,
                and_(
                    ChannelSourceFilter.channel_show_id == ChannelShow.id,
                    ChannelSourceFilter.show_id == Show.id,
                ),
            )
            .outerjoin(
                ChannelSeasonFilter,
                and_(
                    ChannelSeasonFilter.channel_show_id == ChannelShow.id,
                    col(ChannelSeasonFilter.season_identifier)
                    == col(Season.season_identifier),
                ),
            )
            .outerjoin(
                ChannelEpisodeFilter,
                and_(
                    ChannelEpisodeFilter.channel_show_id == ChannelShow.id,
                    col(ChannelEpisodeFilter.episode_identifier)
                    == col(Episode.episode_identifier),
                    or_(
                        col(ChannelEpisodeFilter.expires_at).is_(None),
                        col(ChannelEpisodeFilter.expires_at) > tz_datetime.now(),
                    ),
                ),
            )
        )

    # TODO: Validate
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
                ChannelSavedEpisodeOrder.channel_id == self._channel.id,
                ChannelSavedEpisodeOrder.episode_id == Episode.id,
            ),
        )

    # TODO: Validate
    def _join_last_watched(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        needs_last_watched = any(
            key.field in LAST_WATCHED_COLUMNS for key in self._channel_options.sort_by
        )
        if not needs_last_watched or not self._user:
            return query
        return join_last_watched(query, self._user)

    # TODO: Validate
    @staticmethod
    def _parse_date_filter(
        absolute_date: datetime | None,
        relative_days: int | None,
    ) -> datetime | None:
        if relative_days:
            return tz_datetime.now() - timedelta(days=relative_days)
        return absolute_date

    # TODO: Validate
    def _filter_deleted_media(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return query.where(col(Episode.deleted_at).is_(None))

    # TODO: Validate
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

    # TODO: Validate
    def _filter_metadata_plugins(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Filter out episodes that only stand in for a website's missing metadata.

        TMDB is imported so other websites can borrow what they left out, never so
        its own copy of an episode is watched, so it is never one of the results.
        `Plugin` is already joined by `_filter_by_plugin_visibility`.
        """
        return query.where(Plugin.key != TMDB_PLUGIN_KEY)

    # TODO: Validate
    def _filter_episodes_by_channels(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return (
            query.where(col(ChannelShow.channel_id).in_(self._channel_ids))
            # Only member shows contribute their episodes; filter-only shows
            # (is_blacklist_only=True) exist solely to hold blacklist/whitelist entries.
            .where(col(ChannelShow.is_blacklist_only).is_(False))
            .where(channel_access_condition())
        )

    # TODO: Validate
    def _apply_channel_specific_blacklist(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return query.where(
            ~blacklisted_on_channels_condition(self._channel_ids, tz_datetime.now()),
        )

    # TODO: Validate
    def _filter_by_watch_state(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Drop the episodes the channel's watch-state options hide."""
        if self._user is None:
            return query
        options = self._channel_options
        if options.hide_watched:
            query = query.where(
                hide_watched_condition(
                    self._user,
                    self._parse_date_filter(
                        options.maximum_watch_date_absolute,
                        options.maximum_watch_date_relative,
                    ),
                ),
            )
        if options.hide_unwatched:
            query = query.where(hide_unwatched_condition(self._user))
        if options.hide_partially_watched:
            query = query.where(
                hide_partially_watched_condition(self._user),
            )
        return query

    # TODO: Validate
    def _episode_range_conditions(self) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = []

        # TODO: Validate
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
            self._tmdb_fallbacks.column("episode", "air_date", Episode),
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
            self._tmdb_fallbacks.column("episode", "release_date", Episode),
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
            self._tmdb_fallbacks.column("episode", "duration", Episode),
            self._channel_options.minimum_duration,
            self._channel_options.maximum_duration,
        )
        return conditions

    # TODO: Validate
    def _filter_by_ranges(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        for condition in self._episode_range_conditions():
            query = query.where(condition)
        return query

    # TODO: Validate
    def _result_limit(self) -> int:
        """The number of episodes to return after deduplication."""
        user_limit = self._channel_options.limit
        return min(user_limit or MAX_EPISODES_RETURNED, MAX_EPISODES_RETURNED)

    # TODO: Validate
    def _apply_limit(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        # Fetch up to the hard cap regardless of the requested limit so that the
        # show counts, which drop episodes after the read, can still fill it.
        return query.limit(MAX_EPISODES_RETURNED)

    # TODO: Validate
    def _filter_disabled_sources(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Globally hide episodes from sources the user has disabled.

        Stacks on top of the channel's own source filtering: an episode must pass
        both this and the per-channel `source_ids` filter. `Source` is already
        joined by `_filter_by_plugin_visibility`.
        """
        config = self._source_config
        if config.other_enabled:
            if config.disabled_keys:
                query = query.where(col(Source.key).not_in(config.disabled_keys))
        else:
            query = query.where(col(Source.key).in_(config.enabled_keys))
        return query

    # TODO: Validate
    def _source_rank_columns(self) -> list[ColumnElement[Any]]:
        """The source ranking, left out when the channel has nothing to collapse."""
        if not self._holds_copied_titles:
            return []
        return [self._source_rank_column()]

    # TODO: Validate
    def _source_rank_column(self) -> ColumnElement[Any]:
        """Rank every copy of an episode against the other copies of it.

        Ties rather than numbers the rows so that a copy held by several channels
        keeps one row per channel, which is what names the channels it came from.
        """
        priority = case(
            self._source_config.priority,
            value=col(Source.key),
            else_=self._source_config.other_priority,
        )
        return (
            func.rank()
            .over(
                partition_by=col(Episode.episode_identifier),
                order_by=[priority, col(Episode.id)],
            )
            .label("source_rank")
        )

    # TODO: Validate
    def _deduplicate_unsorted(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Collapse the copies of an episode when nothing has asked for an order."""
        query = self._tmdb_fallbacks.join(query)
        if not self._holds_copied_titles:
            return query
        subquery = query.add_columns(self._source_rank_column()).subquery()
        return select(  # type: ignore[return-value]
            aliased(Episode, subquery),
            subquery.c.channel_id,
        ).where(subquery.c.source_rank == 1)

    # TODO: Validate
    def _rank_fuzzy_values(
        self,
        subquery: Subquery,
        fuzzy_labels: dict[int, str],
        directeds: list[UnaryExpression[Any] | ColumnElement[Any]],
    ) -> Subquery:
        """Number the sort values a fuzzy key holds so its jitter has ranks to move."""
        extra_columns: list[ColumnElement[Any]] = [
            func.dense_rank().over(order_by=directeds[index]).label(label)
            for index, label in fuzzy_labels.items()
        ]
        carried_rank = [subquery.c.source_rank] if self._holds_copied_titles else []
        return (
            select(aliased(Episode, subquery), subquery.c.channel_id)
            .add_columns(
                subquery.c.show_id,
                *carried_rank,
                *(
                    getattr(subquery.c, f"sort_value_{index}")
                    for index in range(len(self._channel_options.sort_by))
                ),
                *extra_columns,
            )
            .subquery()
        )

    # TODO: Validate
    def _sort_and_deduplicate(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        if not self._channel_options.sort_by:
            return self._deduplicate_unsorted(query)
        expressions = self._sort_expressions
        labeled_values: list[ColumnElement[Any]] = [
            expressions.expression(sort_key).label(f"sort_value_{index}")
            for index, sort_key in enumerate(self._channel_options.sort_by)
        ]
        labeled_values.append(col(Season.show_id).label("show_id"))
        labeled_values.extend(self._source_rank_columns())
        # Every filter and sort has now asked for its columns, so the levels they
        # borrowed from TMDB are known and can be joined in before the values are
        # frozen into a subquery.
        query = self._tmdb_fallbacks.join(query)
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
            subquery = self._rank_fuzzy_values(subquery, fuzzy_labels, directeds)
            raws = [
                getattr(subquery.c, f"sort_value_{i}")
                for i in range(len(self._channel_options.sort_by))
            ]
            directeds = [
                expressions.apply_direction(raws[i], key)
                for i, key in enumerate(self._channel_options.sort_by)
            ]

        # TODO: Validate
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
        if self._holds_copied_titles:
            outer = outer.where(subquery.c.source_rank == 1)
        return outer.order_by(*order_by)
