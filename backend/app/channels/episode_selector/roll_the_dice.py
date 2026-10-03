# TODO: Validate

from typing import Any
from uuid import UUID

from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import Session, col, select

from app.channels.episode_selector.sorting import SortExpressionBuilder
from app.channels.episode_selector.watch_filters import started_title_ids
from app.channels.models import ChannelTitle
from app.channels.schemas import ChannelOptions
from app.users.models import User

ROLL_THE_DICE_SORT = [
    ("episode", "last_watched_incomplete", "descending", "sequential"),
    ("title", "random", "ascending", "randomize"),
    ("episode", "random", "ascending", "sequential"),
]


# TODO: Validate
class RollTheDice:
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        user: User | None,
        channel_ids: set[UUID],
        channel_options: ChannelOptions,
        expressions: SortExpressionBuilder,
    ) -> None:
        self._session = session
        self._user = user
        self._channel_ids = channel_ids
        self._channel_options = channel_options
        self._expressions = expressions
        self._pool_was_truncated = False

    # TODO: Validate
    @property
    def recognised(self) -> bool:
        options = self._channel_options
        shape = [
            (key.model, key.field, key.direction, key.order) for key in options.sort_by
        ]
        if shape != ROLL_THE_DICE_SORT:
            return False
        if any(key.aggregation or key.fuzziness or key.days for key in options.sort_by):
            return False
        return (
            options.total_titles_count is None
            and options.started_titles_count is None
            and options.new_titles_count is None
        )

    # TODO: Validate
    @property
    def shuffled_key_index(self) -> int | None:
        return 1 if self.recognised else None

    # TODO: Validate
    def fell_short(
        self,
        deepest_partition_rank: int,
        episode_count: int,
        wanted: int,
    ) -> bool:
        if not self.recognised or not self._pool_was_truncated:
            return False
        return deepest_partition_rank > 1 or episode_count < wanted

    # TODO: Validate
    def titles(self, row_limit: int) -> set[UUID]:
        hashed = self._expressions.random_hash(
            col(ChannelTitle.tmdb_title_id),  # type: ignore[arg-type]
        )
        wanted = row_limit * 4
        shuffled = (
            select(col(ChannelTitle.tmdb_title_id))
            .where(col(ChannelTitle.channel_id).in_(self._channel_ids))
            .where(col(ChannelTitle.is_blacklist_only).is_(False))
            .group_by(col(ChannelTitle.tmdb_title_id))
            .order_by(self._shuffle_order(hashed))
            .limit(wanted)
        )
        titles = set(self._session.exec(shuffled).all())
        self._pool_was_truncated = len(titles) == wanted
        if self._user:
            titles |= set(self._session.exec(started_title_ids(self._user)).all())
        return titles

    # TODO: Validate
    def _shuffle_order(self, hashed: ColumnElement[Any]) -> ColumnElement[Any]:
        return self._expressions.random_hash(hashed)
