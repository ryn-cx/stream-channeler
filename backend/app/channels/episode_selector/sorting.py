# TODO: Validate
"""Turning one of a channel's sort keys into the expression it orders by."""

from datetime import timedelta
from typing import Any

from sqlalchemy import String, case, literal_column
from sqlalchemy.sql.expression import ColumnElement, UnaryExpression
from sqlmodel import and_, col, desc, func, select

from app.channels.episode_selector.tmdb_columns import TMDBFallbackColumns
from app.channels.episode_selector.watch_filters import (
    EPISODE_LAST_WATCHED_SUBQUERY,
    LAST_WATCHED_COLUMNS,
)
from app.channels.models import ChannelSavedEpisodeOrder
from app.channels.schemas import SortKeyInput
from app.episodes.models import Episode
from app.models import ZERO_LAST_SUFFIX
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.utils import tz_datetime
from app.watches.models import Watch

# Stands in for 0 in the `_zero_last` sorts, past any season or episode number a
# website or TMDB issues while still fitting the integer columns it is compared to.
ZERO_LAST_VALUE = 2**31 - 1


def zero_last(number: ColumnElement[Any]) -> ColumnElement[Any]:
    """Return `number` with 0 ordered past every other number rather than ahead.

    A season or an episode numbered 0 is the specials rather than the first of the
    run, so a channel that wants them at the end sorts on this instead. `NULL` is
    left as it is, which keeps it whatever the sort already made of it.
    """
    return case((number == 0, ZERO_LAST_VALUE), else_=number)


class SortExpressionBuilder:
    """Builds the SQL expression behind each of a channel's sort keys."""

    def __init__(
        self,
        random_seed: int,
        user: User | None,
        fallbacks: TMDBFallbackColumns,
    ) -> None:
        """Build the sort expressions for one read of one channel."""
        self._random_seed = random_seed
        self._user = user
        self._fallbacks = fallbacks

    def expression(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        """Return the value `sort_key` orders episodes by."""
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
        """Point `expr` the way `sort_key` asks, and place its nulls."""
        directed: UnaryExpression[Any] | ColumnElement[Any] = (
            desc(expr) if sort_key.direction == "descending" else expr
        )
        if sort_key.field in LAST_WATCHED_COLUMNS and sort_key.direction == "ascending":
            return directed.nulls_first()
        return directed.nulls_last()

    def random_hash(self, expr: ColumnElement[Any]) -> ColumnElement[Any]:
        """Shuffle `expr` into an order that holds for this channel's seed."""
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
            return func.count(Episode.id).over(partition_by=col(Show.id))  # type: ignore[arg-type]
        if field == "started" and sort_key.model == "show":
            return self._started_show_expr()

        return self._stored_column(sort_key.model, field, sort_key.model_class)

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
            episode_field = self._stored_column("episode", sort_key.field, Episode)

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

        Two websites number the same media differently, so the order goes by
        TMDB's numbering alone and the copies TMDB has no number for follow
        every copy it does, in the order their own website put them. Ranking
        runs over the whole title rather than one website's copy of it, since a
        website that carries only a later season would otherwise have its first
        season rank alongside another website's first.

        Which season an episode belongs to is TMDB's answer as well, taken from
        the episode's own TMDB counterpart rather than from the season the
        website filed it under. A website that files a special alongside a
        season's episodes still has it sorted where TMDB keeps it, and a season
        whose own link is the only one there is stands in for an episode TMDB
        does not have.

        `zero_last_numbers` ranks a season or an episode numbered 0 after the rest
        of the run rather than ahead of it, which is where the specials belong.
        """

        def numbered(number: ColumnElement[Any]) -> ColumnElement[Any]:
            return zero_last(number) if zero_last_numbers else number

        if model == "episode":
            tmdb_number = numbered(self._fallbacks.number("episode"))
            return func.dense_rank().over(
                partition_by=func.coalesce(
                    self._fallbacks.episode_season("season_identifier"),
                    col(Season.season_identifier),
                ),
                order_by=(
                    case((tmdb_number.is_(None), 1), else_=0),
                    tmdb_number,
                    case(
                        (tmdb_number.is_(None), numbered(col(Episode.episode_number))),
                    ),
                ),
            )
        if model == "season":
            tmdb_number = numbered(
                func.coalesce(
                    self._fallbacks.episode_season("season_number"),
                    self._fallbacks.number("season"),
                ),
            )
            return func.dense_rank().over(
                partition_by=col(Show.show_identifier),
                order_by=(
                    case((tmdb_number.is_(None), 1), else_=0),
                    tmdb_number,
                    case(
                        (tmdb_number.is_(None), numbered(col(Season.season_number))),
                    ),
                    case((tmdb_number.is_(None), col(Season.sort_order))),
                ),
            )
        msg = f"sequential is not supported for model '{model}'"
        raise ValueError(msg)

    def _recently_aired_expr(self, sort_key: SortKeyInput) -> ColumnElement[Any]:
        cutoff = sort_key.recently_aired_date or (
            tz_datetime.now() - timedelta(days=sort_key.days or 7)
        )
        air_date = self._fallbacks.column("episode", "air_date", Episode)
        return case(
            (and_(air_date.is_not(None), air_date >= cutoff), 1),
            else_=0,
        )

    def _started_show_expr(self) -> ColumnElement[Any]:
        if not self._user:
            return literal_column("0")
        started_query = (
            select(Watch.id)
            .join(Watch.episodes)  # type: ignore[arg-type]
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
