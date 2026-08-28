# TODO: Validate
"""Reading the episodes a channel offers, in the order it offers them."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, distinct
from sqlalchemy.orm import Mapped, selectinload
from sqlalchemy.sql.expression import ColumnElement, Subquery, UnaryExpression
from sqlmodel import and_, col, func, or_, select
from sqlmodel.sql.expression import Select

from app.auth.dependencies import CurrentUser, SessionDep
from app.canonical_media.episodes import canonical_id_of, links_of
from app.canonical_media.filters import is_canonical, is_non_canonical
from app.canonical_media.keys import not_tmdb_key_clause, same_issuer_clause
from app.channel_orders.models import ChannelOrder
from app.channels.channel_scope import (
    channel_attribution,
    child_channel_ids,
    resolve_channel_ids,
)
from app.channels.episode_selector.canonical_columns import CanonicalColumns
from app.channels.episode_selector.canonical_entities import (
    CANONICAL_EPISODE,
    CANONICAL_EPISODE_LINK,
    CANONICAL_SEASON,
    CANONICAL_SHOW,
    episode_id,
    season_id,
)
from app.channels.episode_selector.order_composition import OrderByComposer
from app.channels.episode_selector.show_counts import selected_show_ids
from app.channels.episode_selector.sorting import SortExpressionBuilder
from app.channels.episode_selector.source_dedup import source_dedup_config
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
    started_show_ids,
)
from app.channels.models import (
    Channel,
    ChannelEpisodeFilter,
    ChannelEpisodeSourceFilter,
    ChannelSavedEpisodeOrder,
    ChannelSeasonFilter,
    ChannelShow,
    ChannelSourceFilter,
)
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.models import Watch

MAX_EPISODES_RETURNED = 1000


# TODO: Validate
def _media_id(episode: Episode) -> UUID:
    """Return the media `episode` is linked to, for grouping its rows by."""
    return canonical_id_of(episode)


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
        self.has_more = False
        self._set_channel_options(channel_options)

        self._channel_ids = self._fetch_channel_ids()

        self.source_config = source_dedup_config(session, self._user)
        self._holds_copied_titles = self._fetch_holds_copied_titles()

        self._canonical_columns = CanonicalColumns()
        self._sort_expressions = SortExpressionBuilder(
            random_seed=self._channel_options.random_seed,
            user=self._user,
            fallbacks=self._canonical_columns,
            # Only a read that orders by the channel an episode comes from has to
            # work out which channel that is.
            channel_attribution=(
                channel_attribution(session, self._user, self._channel)
                if any(key.model == "channel" for key in self._channel_options.sort_by)
                else {}
            ),
            # Read once rather than per candidate row: the titles a user has
            # started are the same set however many episodes are being ordered.
            started_shows=self._fetch_started_shows(),
        )

    # TODO: Validate
    def _fetch_started_shows(self) -> set[UUID]:
        needs_started = any(
            key.field == "started" and key.model == "show"
            for key in self._channel_options.sort_by
        )
        if not needs_started or not self._user:
            return set()
        return set(self._session.exec(started_show_ids(self._user)).all())

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
                requested_limit = self._channel_options.limit
                self._channel_options = ChannelOptions.model_validate_json(order.config)
                self._channel_options.limit = requested_limit

    # TODO: Validate
    def _filter_channel_options(
        self,
    ) -> None:
        """Remove channel options that require the user to be logged in if they are not logged in."""
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
        """Whether the channel can hold a title as more than one non-canonical row.

        Collapsing the non-canonical rows of an episode means reading every episode the
        channel offers before any of them can be returned, since a non-canonical row the
        row limit never reached may be the one that wins. A channel with no title to
        collapse skips the ranking and lets the limit stop it early instead.

        Asked of the titles rather than of their episodes, which is what keeps it cheap:
        a channel holds tens of titles where it offers thousands of episodes. One
        website carrying a title twice counts as much as two websites carrying it once,
        since either leaves an episode with a non-canonical row to be ranked against.
        """
        # A title nothing else holds a record of is watched on the row that is the
        # record, so it is its own non-canonical row and there is no link to reach it
        # by. Outer-joined so those titles are still counted, as the one non-canonical
        # row they are.
        totals = (
            select(
                func.count(distinct(col(Show.source_id))),
                func.count(distinct(col(Show.id))),
                func.count(distinct(col(ChannelShow.canonical_show_id))),
            )
            .select_from(ChannelShow)
            .outerjoin(
                ShowCanonicalShow,
                col(ShowCanonicalShow.canonical_show_id)
                == col(ChannelShow.canonical_show_id),
            )
            .join(
                Show,
                col(Show.id)
                == func.coalesce(
                    col(ShowCanonicalShow.show_id),
                    col(ChannelShow.canonical_show_id),
                ),
            )
            .where(col(ChannelShow.channel_id).in_(self._channel_ids))
            .where(col(ChannelShow.is_blacklist_only).is_(False))
            # A title TMDB wrote and no website carries is watched nowhere, so it is no
            # non-canonical row of anything and nothing has to be ranked against it.
            .where(
                or_(
                    is_non_canonical(Show),
                    not_tmdb_key_clause(col(Show.key)),
                ),
            )
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
        ordered_episodes, channels_by_media = self._read_ordered_episodes()
        shows = selected_show_ids(
            self._session,
            self._user,
            ordered_episodes,
            self._channel_options,
        )
        if shows is not None:
            ordered_episodes, channels_by_media = self._read_ordered_episodes(shows)
        page_start = self._channel_options.offset
        page_end = page_start + self._result_limit()
        self.has_more = len(ordered_episodes) > page_end
        ordered_episodes = ordered_episodes[page_start:page_end]

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
                channel_id=channels_by_media[_media_id(episode)][0],
                channel_ids=channels_by_media[_media_id(episode)],
                latest_watch=watches.get(_media_id(episode)),
            )
            for episode in ordered_episodes
        ]

    # TODO: Validate
    def _read_ordered_episodes(
        self,
        shows: set[UUID] | None = None,
    ) -> tuple[list[Episode], dict[UUID, list[UUID]]]:
        query = self._base_query()
        query = self._join_whitelist(query)
        query = self._join_saved_order(query)
        query = self._filter_deleted_media(query)
        query = self._filter_episodes_by_channels(query)
        query = self._apply_channel_specific_blacklist(query)
        query = self._join_plugin_and_filter_sources(query)
        query = self._filter_metadata_plugins(query)
        query = self._filter_disabled_sources(query)
        query = self._filter_by_watch_state(query)
        query = self._filter_by_ranges(query)
        if shows is not None:
            query = query.where(self._canonical_columns.show_id().in_(shows))
        narrowed = self._sort_and_deduplicate(query)
        narrowed = self._apply_limit(narrowed, restricted=shows is not None)

        rows = self._session.exec(narrowed).all()
        episodes_by_id = self._load_episodes({row[0] for row in rows})

        ordered_episodes: list[Episode] = []
        channels_by_media: dict[UUID, list[UUID]] = {}
        for row_episode_id, channel_id in rows:
            episode = episodes_by_id[row_episode_id]
            media_id = _media_id(episode)
            if media_id not in channels_by_media:
                channels_by_media[media_id] = []
                ordered_episodes.append(episode)
            if channel_id not in channels_by_media[media_id]:
                channels_by_media[media_id].append(channel_id)
        return ordered_episodes, channels_by_media

    # TODO: Validate
    def _load_episodes(self, episode_ids: set[UUID]) -> dict[UUID, Episode]:
        query = (
            select(Episode)
            .where(col(Episode.id).in_(episode_ids))
            .options(
                selectinload(Episode.season)  # type: ignore[arg-type]
                .selectinload(Season.show)  # type: ignore[arg-type]
                .selectinload(Show.source)  # type: ignore[arg-type]
                .selectinload(Source.plugin),  # type: ignore[arg-type]
                selectinload(Episode.canonical_episode_links),  # type: ignore[arg-type]
            )
        )
        return {episode.id: episode for episode in self._session.exec(query).all()}

    # TODO: Validate
    def _narrowed(
        self,
        query: Select[tuple[Episode, UUID]],
        extra_columns: list[ColumnElement[Any]],
    ) -> Subquery:
        return query.with_only_columns(
            col(Episode.id).label("id"),
            col(ChannelShow.channel_id).label("channel_id"),
            *extra_columns,
        ).subquery()

    # TODO: Validate
    def _base_query(self) -> Select[tuple[Episode, UUID]]:
        # A channel holds titles rather than one website's non-canonical row of them, so
        # every non-canonical row of a title the channel holds is joined to the same
        # `ChannelShow`.
        #
        # Which title an episode belongs to is read off the episode rather than
        # off the listing holding it, because a listing can hold more than one:
        # a channel that was told to hold one of the titles a listing mixes gets
        # that title's episodes and not the listing's other ones.
        #
        # Every join here is now the same table reached again, so each side says
        # which of the two it means. What the query returns is the listings, and
        # what it walks up through is the media they are listings of.
        query: Select[tuple[Episode, UUID]] = (
            select(Episode, ChannelShow.channel_id)  # type: ignore[call-overload]
            .select_from(Episode)
            .join(Season, col(Episode.season_id) == col(Season.id))
            .join(Show, col(Season.show_id) == col(Show.id))
            # A listing stands for every episode it was linked to, so one that
            # runs two episodes together is read once under each of them: the
            # channel holds episodes rather than listings, and a listing standing
            # for two of them answers for both.
            .outerjoin(
                CANONICAL_EPISODE_LINK,
                links_of(Episode, CANONICAL_EPISODE_LINK),
            )
        )
        query = self._join_last_watched(query)
        return (
            query.outerjoin(
                CANONICAL_EPISODE,
                and_(
                    col(CANONICAL_EPISODE_LINK.canonical_episode_id)
                    == col(CANONICAL_EPISODE.id),
                    is_canonical(CANONICAL_EPISODE),
                ),
            )
            .outerjoin(
                CANONICAL_SEASON,
                col(CANONICAL_EPISODE.season_id) == col(CANONICAL_SEASON.id),
            )
            # An episode nothing was minted for it to be linked to is the episode
            # itself, so there is no canonical row to read the title off and the
            # title is the one its website's listing is linked to instead. Joined
            # only for those episodes, since a listing linked to more than one
            # title would otherwise put every episode of it under each of them.
            .outerjoin(
                ShowCanonicalShow,
                and_(
                    col(ShowCanonicalShow.show_id) == col(Show.id),
                    is_canonical(Episode),
                ),
            )
            # A row nothing else holds a record of is the record, and it is also
            # where the media is watched, so it is its own title and answers for
            # itself when neither the episode nor a link has an answer. TMDB's own
            # rows are titles that are watched nowhere and are left out by
            # `_filter_metadata_plugins` rather than here.
            .join(
                ChannelShow,
                col(ChannelShow.canonical_show_id)
                == func.coalesce(
                    col(CANONICAL_SEASON.show_id),
                    col(ShowCanonicalShow.canonical_show_id),
                    case((is_canonical(Show), col(Show.id))),
                ),
            )
            .join(
                CANONICAL_SHOW,
                and_(
                    col(CANONICAL_SHOW.id) == col(ChannelShow.canonical_show_id),
                    is_canonical(CANONICAL_SHOW),
                ),
            )
            # A website files under a title seasons the title has no record of -
            # a film it sells as part of the series, a run of extras - and a
            # canonical season is minted for each so its episodes have somewhere
            # to hang. The season is the website's own rather than one of the
            # title's, so the episodes under it are no part of what the channel
            # offers. Told apart by who issued the key: a season of the title
            # carries the issuer the title itself was named by. An episode with no
            # canonical season has none of this to be told apart by and is taken
            # on the strength of the link its listing carries.
            .where(
                or_(
                    col(CANONICAL_SEASON.key).is_(None),
                    same_issuer_clause(
                        col(CANONICAL_SHOW.key),
                        col(CANONICAL_SEASON.key),
                    ),
                ),
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
                    col(ChannelSeasonFilter.season_id) == season_id(),
                ),
            )
            .outerjoin(
                ChannelEpisodeFilter,
                and_(
                    ChannelEpisodeFilter.channel_show_id == ChannelShow.id,
                    col(ChannelEpisodeFilter.canonical_episode_id) == episode_id(),
                    or_(
                        col(ChannelEpisodeFilter.expires_at).is_(None),
                        col(ChannelEpisodeFilter.expires_at) > tz_datetime.now(),
                    ),
                ),
            )
            # A row of this one is about the linked episode being read rather than
            # the episode itself, so the website's linked show has to match too.
            .outerjoin(
                ChannelEpisodeSourceFilter,
                and_(
                    ChannelEpisodeSourceFilter.channel_show_id == ChannelShow.id,
                    col(ChannelEpisodeSourceFilter.canonical_episode_id)
                    == episode_id(),
                    ChannelEpisodeSourceFilter.show_id == Show.id,
                    or_(
                        col(ChannelEpisodeSourceFilter.expires_at).is_(None),
                        col(ChannelEpisodeSourceFilter.expires_at) > tz_datetime.now(),
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
                col(ChannelSavedEpisodeOrder.canonical_episode_id) == episode_id(),
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
    def _join_plugin_and_filter_sources(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        query = query.join(Source, col(Show.source_id) == Source.id).join(
            Plugin,
            col(Source.plugin_id) == Plugin.id,
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

        TMDB is imported so other websites can borrow what they left out, never so its
        own non-canonical row of an episode is watched, so it is never one of the
        results.
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
            self._canonical_columns.column("episode", "air_date", Episode),
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
            self._canonical_columns.column("episode", "duration", Episode),
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
        """Return the number of episodes to keep after deduplication."""
        user_limit = self._channel_options.limit
        return min(user_limit or MAX_EPISODES_RETURNED, MAX_EPISODES_RETURNED)

    # TODO: Validate
    def _apply_limit(
        self,
        query: Select[tuple[UUID, UUID]],
        *,
        restricted: bool = False,
    ) -> Select[tuple[UUID, UUID]]:
        # Fetch up to the hard cap regardless of the requested limit so that the
        # show counts, which drop episodes after the read, can still fill it.
        return query.limit(self._sql_limit(restricted=restricted))

    # TODO: Validate
    def _sql_limit(self, *, restricted: bool = False) -> int:
        options = self._channel_options
        if not restricted and (
            options.total_shows_count is not None
            or options.started_shows_count is not None
            or options.new_shows_count is not None
        ):
            return MAX_EPISODES_RETURNED
        rows_per_episode = max(len(self._channel_ids), 1)
        wanted = options.offset + self._result_limit() + 1
        return min(wanted * rows_per_episode, MAX_EPISODES_RETURNED)

    # TODO: Validate
    def _filter_disabled_sources(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[Episode, UUID]]:
        """Globally hide episodes from sources the user has disabled.

        Stacks on top of the channel's own source filtering: an episode must pass
        both this and the per-channel `source_ids` filter.
        """
        config = self.source_config
        if config.other_enabled:
            if config.disabled_keys:
                query = query.where(col(Source.key).not_in(config.disabled_keys))
        else:
            query = query.where(col(Source.key).in_(config.enabled_keys))
        return query

    # TODO: Validate
    def _source_rank_columns(self) -> list[ColumnElement[Any]]:
        """Return the source ranking, left out when the channel has nothing to collapse."""
        if not self._holds_copied_titles:
            return []
        return [self._source_rank_column()]

    # TODO: Validate
    def _source_rank_column(self) -> ColumnElement[Any]:
        """Rank every non-canonical row of an episode against the others of it.

        Ties rather than numbers the rows so that a non-canonical row held by several
        channels keeps one row per channel, which is what names the channels it came
        from.
        """
        priority = case(
            self.source_config.priority,
            value=col(Source.key),
            else_=self.source_config.other_priority,
        )
        return (
            func.rank()
            .over(
                partition_by=episode_id(),
                order_by=[priority, col(Episode.id)],
            )
            .label("source_rank")
        )

    # TODO: Validate
    def _deduplicate_unsorted(
        self,
        query: Select[tuple[Episode, UUID]],
    ) -> Select[tuple[UUID, UUID]]:
        """Collapse an episode's non-canonical rows when nothing asked for an order."""
        if not self._holds_copied_titles:
            return query.with_only_columns(  # type: ignore[return-value]
                col(Episode.id).label("id"),
                col(ChannelShow.channel_id).label("channel_id"),
            )
        subquery = self._narrowed(query, [self._source_rank_column()])
        return select(
            subquery.c.id,
            subquery.c.channel_id,
        ).where(subquery.c.source_rank == 1)

    # TODO: Validate
    def _rank_fuzzy_values(
        self,
        subquery: Subquery,
        fuzzy_labels: dict[int, str],
        directeds: list[UnaryExpression[Any] | ColumnElement[Any]],
    ) -> Subquery:
        """Order the sort values a fuzzy key holds so its jitter has ranks to move."""
        extra_columns: list[ColumnElement[Any]] = [
            func.dense_rank().over(order_by=directeds[index]).label(label)
            for index, label in fuzzy_labels.items()
        ]
        carried_rank = [subquery.c.source_rank] if self._holds_copied_titles else []
        return (
            select(subquery.c.id, subquery.c.channel_id)
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
    ) -> Select[tuple[UUID, UUID]]:
        if not self._channel_options.sort_by:
            return self._deduplicate_unsorted(query)
        expressions = self._sort_expressions
        labeled_values: list[ColumnElement[Any]] = [
            expressions.expression(sort_key).label(f"sort_value_{index}")
            for index, sort_key in enumerate(self._channel_options.sort_by)
        ]
        # The title rather than the website's listing of it, so the last tie-break
        # keeps a title together however many websites and listings carry it.
        labeled_values.append(
            self._canonical_columns.show_id().label("show_id"),
        )
        labeled_values.extend(self._source_rank_columns())
        subquery = self._narrowed(query, labeled_values)

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

        if self._holds_copied_titles:
            subquery = select(subquery).where(subquery.c.source_rank == 1).subquery()

        subquery, order_by = OrderByComposer(
            expressions,
            self._channel_options.sort_by,
            fuzzy_labels,
        ).compose(subquery)
        order_by.extend([subquery.c.show_id, subquery.c.id])

        outer: Select[tuple[UUID, UUID]] = select(
            subquery.c.id,
            subquery.c.channel_id,
        )
        return outer.order_by(*order_by)
