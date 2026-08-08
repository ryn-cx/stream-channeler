# TODO: Validate
"""Reading the episodes a channel offers, in the order it offers them."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Mapped, aliased
from sqlalchemy.sql.expression import ColumnElement, UnaryExpression
from sqlmodel import and_, col, func, or_, select
from sqlmodel.sql.expression import Select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channel_orders.models import ChannelOrder
from app.channels.episode_selector.channel_scope import (
    channel_attribution,
    child_channel_ids,
    resolve_channel_ids,
)
from app.channels.episode_selector.show_counts import limit_shows
from app.channels.episode_selector.sorting import SortExpressionBuilder
from app.channels.episode_selector.source_dedup import (
    SourceDedupConfig,
    deduplicate_episodes,
    source_dedup_config,
)
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
from app.users.service import stored_preferences
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000


@dataclass
class EpisodeResult:
    episode: Episode
    channel_id: UUID
    channel_ids: list[UUID]
    latest_watch: Watch | None = None


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
            session,
            stored_preferences(self._user.source_preferences) if self._user else [],
        )
        self._tmdb_fallbacks = TMDBFallbackColumns()
        self._sort_expressions = SortExpressionBuilder(
            random_seed=self._channel_options.random_seed,
            user=self._user,
            fallbacks=self._tmdb_fallbacks,
            channel_attribution=channel_attribution(session, self._user, channel),
        )

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
                channel_id=channels_by_episode[episode.id][0],
                channel_ids=channels_by_episode[episode.id],
                latest_watch=watches.get(episode.episode_identifier),
            )
            for episode in ordered_episodes
        ]

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
                        col(ChannelEpisodeFilter.expires_at) > self._now,
                    ),
                ),
            )
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

    def _apply_channel_specific_blacklist(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        return query.where(
            ~blacklisted_on_channels_condition(self._channel_ids, self._now),
        )

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

    def _source_keys_by_episode(
        self,
        episodes: Sequence[Episode],
    ) -> dict[UUID, str]:
        """Map each episode id to its owning source's key."""
        if not episodes:
            return {}
        rows = self._session.exec(
            select(Episode.id, Source.key)  # type: ignore[call-overload]
            .select_from(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .where(col(Episode.id).in_([episode.id for episode in episodes])),
        ).all()
        return dict(rows)

    def _deduplicate_by_identifier(
        self,
        episodes: list[Episode],
    ) -> list[Episode]:
        """Collapse episodes sharing an `episode_identifier` by source priority."""
        source_keys = self._source_keys_by_episode(episodes)
        return deduplicate_episodes(episodes, source_keys, self._source_config)

    def _sort_episodes(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        if not self._channel_options.sort_by:
            return self._tmdb_fallbacks.join(query)
        expressions = self._sort_expressions
        labeled_values: list[ColumnElement[Any]] = [
            expressions.expression(sort_key).label(f"sort_value_{index}")
            for index, sort_key in enumerate(self._channel_options.sort_by)
        ]
        labeled_values.append(col(Season.show_id).label("show_id"))
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
