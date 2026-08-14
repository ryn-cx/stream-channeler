# TODO: Validate
"""Turning one of a channel's sort keys into the expression it orders by."""

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import String, case, literal, literal_column
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import ColumnElement, UnaryExpression
from sqlmodel import and_, col, desc, func, select

from app.canonical_media.filters import is_canonical
from app.channels.episode_selector.canonical_columns import CanonicalColumns
from app.channels.episode_selector.canonical_entities import (
    CANONICAL_EPISODE,
    CANONICAL_SEASON,
    CANONICAL_SHOW,
    episode_id,
)
from app.channels.episode_selector.watch_filters import (
    EPISODE_LAST_WATCHED_SUBQUERY,
    LAST_WATCHED_COLUMNS,
)
from app.channels.models import ChannelSavedEpisodeOrder, ChannelShow
from app.channels.schemas import SortKeyInput
from app.episodes.models import Episode
from app.models import ZERO_LAST_SUFFIX
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source
from app.users.models import User
from app.utils import tz_datetime
from app.watches.models import Watch

# Stands in for 0 in the `_zero_last` sorts, past any season or episode number a
# website or TMDB issues while still fitting the integer columns it is compared to.
ZERO_LAST_VALUE = 2**31 - 1


# TODO: Validate
def zero_last(number: ColumnElement[Any]) -> ColumnElement[Any]:
    """Return `number` with 0 ordered past every other number rather than ahead.

    A season or an episode numbered 0 is the specials rather than the first of the
    run, so a channel that wants them at the end sorts on this instead. `NULL` is
    left as it is, which keeps it whatever the sort already made of it.
    """
    return case((number == 0, ZERO_LAST_VALUE), else_=number)


# TODO: Validate
class SortExpressionBuilder:
    """Builds the SQL expression behind each of a channel's sort keys."""

    # TODO: Validate
    def __init__(
        self,
        random_seed: int,
        user: User | None,
        fallbacks: CanonicalColumns,
        channel_attribution: dict[UUID, UUID] | None = None,
    ) -> None:
        """Build the sort expressions for one read of one channel."""
        self._random_seed = random_seed
        self._user = user
        self._fallbacks = fallbacks
        self._channel_attribution = channel_attribution or {}

    # TODO: Validate
    def expression(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        """Return the value `sort_key` orders episodes by."""
        if sort_key.field == "saved_order":
            return col(ChannelSavedEpisodeOrder.position)
        if sort_key.aggregation and sort_key.model == "episode":
            return self._aggregate_episode_expr(sort_key)
        return self._value_expr(sort_key)

    # TODO: Validate
    @staticmethod
    def apply_direction(
        expr: ColumnElement[Any],
        sort_key: SortKeyInput,
    ) -> UnaryExpression[Any] | ColumnElement[Any]:
        """Point `expr` the way `sort_key` asks, and place its nulls."""
        directed: UnaryExpression[Any] | ColumnElement[Any] = (
            desc(expr) if sort_key.direction == "descending" else expr
        )
        if sort_key.field in LAST_WATCHED_COLUMNS and sort_key.direction == "ascending":
            return directed.nulls_first()
        return directed.nulls_last()

    # TODO: Validate
    def random_hash(self, expr: ColumnElement[Any]) -> ColumnElement[Any]:
        """Shuffle `expr` into an order that holds for this channel's seed."""
        return func.hashtext(
            func.concat(
                func.cast(expr, String),
                str(self._random_seed),
            ),
        )

    # TODO: Validate
    def _channel_expr(self) -> ColumnElement[Any]:
        """Return the channel an episode reads as coming from.

        An episode is held by whichever channel down the chain carries the title,
        which is not the channel it was added through, so the channels combined
        into this one stand for everything they reach.
        """
        source_channel = col(ChannelShow.channel_id)
        if not self._channel_attribution:
            return source_channel
        return case(
            *(
                (source_channel == channel_id, literal(str(added_through)))
                for channel_id, added_through in self._channel_attribution.items()
            ),
            else_=func.cast(source_channel, String),
        )

    # TODO: Validate
    def _value_expr(self, sort_key: SortKeyInput) -> ColumnElement[Any]:  # noqa: PLR0911
        field = sort_key.field

        if sort_key.model == "channel":
            channel_expr = self._channel_expr()
            # Shuffling the channels themselves keeps every episode of one of them
            # together, which is what a random sort on a channel is asking for.
            return self.random_hash(channel_expr) if field == "random" else channel_expr
        if field == "random":
            # The media a copy is of rather than the copy, so every website's copy
            # of one episode is shuffled to the same place and a title stays
            # together however many websites carry it.
            random_ids: dict[str, Any] = {
                "episode": episode_id(),
                "season": self._fallbacks.episode_season_id(),
                "show": self._fallbacks.show_id(),
                "source": Source.id,
                "plugin": Plugin.id,
            }
            return self.random_hash(random_ids[sort_key.model])
        if field in {"sequential", "sequential_zero_last"}:
            return self._sequential_rank(
                sort_key.model,
                zero_last_numbers=field.endswith(ZERO_LAST_SUFFIX),
            )
        if field == "recently_aired":
            return self._recently_aired_expr(sort_key)
        if field in LAST_WATCHED_COLUMNS:
            return literal_column(
                f"{EPISODE_LAST_WATCHED_SUBQUERY}.{LAST_WATCHED_COLUMNS[field]}",
            )
        if field == "episode_count":
            return func.count(episode_id()).over(
                partition_by=self._fallbacks.show_id(),
            )
        if field == "started" and sort_key.model == "show":
            return self._started_show_expr()

        return self._stored_column(sort_key.model, field, sort_key.model_class)

    # TODO: Validate
    def _stored_column(
        self,
        model: str,
        field: str,
        model_class: type[Any],
    ) -> ColumnElement[Any]:
        """Return the column `field` names, ordering 0 last when it asks for that."""
        base_field = field.removesuffix(ZERO_LAST_SUFFIX)
        column = self._fallbacks.column(model, base_field, model_class)
        if base_field == field:
            return column
        return zero_last(column)

    # TODO: Validate
    def _aggregate_episode_expr(
        self,
        sort_key: SortKeyInput,
    ) -> ColumnElement[Any]:
        if sort_key.field in LAST_WATCHED_COLUMNS:
            return literal_column(
                f"{EPISODE_LAST_WATCHED_SUBQUERY}.{LAST_WATCHED_COLUMNS[sort_key.field]}",
            )

        if sort_key.field == "random":
            episode_field: ColumnElement[Any] = self.random_hash(
                self._fallbacks.show_id(),
            )
        elif sort_key.field == "recently_aired":
            episode_field = self._recently_aired_expr(sort_key)
        elif sort_key.field == "episode_count":
            episode_field = episode_id()
        else:
            episode_field = self._stored_column(
                "episode",
                sort_key.field,
                CANONICAL_EPISODE,
            )

        agg_funcs: dict[str, Any] = {
            "max": func.max,
            "min": func.min,
            "avg": func.avg,
        }
        agg_func = agg_funcs.get(sort_key.aggregation)  # type: ignore[arg-type]
        if agg_func is None:
            msg = f"Unsupported aggregation '{sort_key.aggregation}'"
            raise ValueError(msg)
        # Aggregated over the title rather than over one website's copy of it, so
        # a channel carrying a title twice reads one number for it either way.
        return agg_func(episode_field).over(partition_by=self._fallbacks.show_id())

    # TODO: Validate
    def _sequential_rank(
        self,
        model: str,
        *,
        zero_last_numbers: bool = False,
    ) -> ColumnElement[Any]:
        """Dense rank computed inline so filters like hide_watched shrink it.

        Emitted as a window function in the post-filter subquery rather than
        a pre-aggregated sibling query, which means the rank reflects
        position within the visible set rather than position within the
        full table.

        Two websites number the same media differently, so the order goes by the
        numbering the canonical row carries and by nothing else. Ranking runs
        over the whole title rather than one website's copy of it, since a
        website that carries only a later season would otherwise have its first
        season rank alongside another website's first. A canonical row with no
        number of its own follows every row that has one, ordered by where the
        row itself says it sits.

        Which season an episode belongs to is the canonical answer as well, taken
        from the episode's own canonical row rather than from the season the
        website filed it under. A website that files a special alongside a
        season's episodes still has it sorted where the canonical hierarchy keeps
        it.

        `zero_last_numbers` ranks a season or an episode numbered 0 after the rest
        of the run rather than ahead of it, which is where the specials belong.
        """

        # TODO: Validate
        def numbered(number: ColumnElement[Any]) -> ColumnElement[Any]:
            return zero_last(number) if zero_last_numbers else number

        if model == "episode":
            canonical_number = numbered(self._fallbacks.number("episode"))
            return func.dense_rank().over(
                partition_by=self._fallbacks.episode_season_id(),
                order_by=(
                    case((canonical_number.is_(None), 1), else_=0),
                    canonical_number,
                    self._fallbacks.column("episode", "sort_order", CANONICAL_EPISODE),
                ),
            )
        if model == "season":
            canonical_number = numbered(self._fallbacks.number("season"))
            return func.dense_rank().over(
                partition_by=self._fallbacks.show_id(),
                order_by=(
                    case((canonical_number.is_(None), 1), else_=0),
                    canonical_number,
                    self._fallbacks.column("season", "sort_order", CANONICAL_SEASON),
                ),
            )
        msg = f"sequential is not supported for model '{model}'"
        raise ValueError(msg)

    # TODO: Validate
    def _recently_aired_expr(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        cutoff = sort_key.recently_aired_date or (
            tz_datetime.now() - timedelta(days=sort_key.days or 7)
        )
        air_date = self._fallbacks.column("episode", "air_date", CANONICAL_EPISODE)
        return case(
            (and_(air_date.is_not(None), air_date >= cutoff), 1),
            else_=0,
        )

    # TODO: Validate
    def _started_show_expr(self) -> ColumnElement[Any]:
        """Whether the `User` has watched anything of the title this episode is of.

        A watch is recorded against the episode itself rather than against the
        copy that played it, so a title counts as started whichever website it was
        started on. An episode nothing was minted for it to be a copy of hangs off
        a website's own listing, so the titles it counts towards are the ones that
        listing is a copy of - all of them, since a listing is no more a copy of
        one title than of another.
        """
        if not self._user:
            return literal_column("0")
        watched_episode = aliased(Episode)
        watched_season = aliased(Season)
        watched_show = aliased(Show)
        watched_link = aliased(ShowCanonicalShow)
        started_query = (
            select(Watch.id)
            .join(
                watched_episode,
                col(watched_episode.watch_identifier) == col(Watch.watch_identifier),
            )
            .join(
                watched_season,
                col(watched_episode.season_id) == col(watched_season.id),
            )
            .join(watched_show, col(watched_season.show_id) == col(watched_show.id))
            # A title has no links and stands for itself; a listing has one row
            # per title it is a copy of and stands for each.
            .outerjoin(watched_link, col(watched_link.show_id) == col(watched_show.id))
            .where(
                and_(
                    is_canonical(watched_episode),
                    func.coalesce(
                        col(watched_link.canonical_show_id),
                        col(watched_show.id),
                    )
                    == self._fallbacks.show_id(),
                    Watch.user_id == self._user.id,
                ),
            )
            .correlate(CANONICAL_SHOW)
            .limit(1)
        )
        return case((started_query.exists(), 1), else_=0)
