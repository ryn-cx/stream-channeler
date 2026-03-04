import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, override

from sqlalchemy import util
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
)

from app.models import BaseMediaMixin, MetadataMixin
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.channels.models import ChannelSeasonWhiteList
    from app.episodes.models import Episode


class BaseSeason(BaseMediaMixin):
    sort_order: int | None = Field(default=None)
    name: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)


class Season(BaseSeason, MetadataMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        # Filtering options.
        Index("Season-sort_order-index", "sort_order"),
        Index("Season-season_number-index", "season_number"),
        Index("Season-name-index", "name"),
        # Deleted filtering.
        Index("Season-deleted_at-index", "deleted_at"),
    )

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(back_populates="seasons")

    episodes: list[Episode] = Relationship(back_populates="season", cascade_delete=True)
    channel_white_list: list[ChannelSeasonWhiteList] = Relationship(
        back_populates="season",
        cascade_delete=True,
    )

    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id)
            .select_from(Show)
            .join(Source)
            .join(Plugin)
            .where(Show.id == self.show_id),
        ).first()

    @override
    def parent(self) -> Show:
        return self.show

    @override
    def children(self) -> list[Episode]:
        return self.episodes

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        show: Show,
        season_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Season | None:
        """Wrap `db.get(Season, ...)` for easier use.

        Args:
            db: Database session.
            show: Parent show instance.
            season_key: Unique ID of the season within the show.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Season instance if Season is found.
            - None if no Season is found.

        """
        return db.get(
            Season,
            (show.id, season_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        show: Show,
        season_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Season:
        """Wrap `db.get_one(Season, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            show: Parent show instance.
            season_key: Unique ID of the season within the show.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Season instance

        Raises:
            NoResultFound: If no season with the given ID exists in the show

        """
        return db.get_one(
            Season,
            (show.id, season_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(
        cls,
        db: Session,
        show: Show,
        season_key: str,
    ) -> Season | None:
        """Like Season.get but will only return a Season if it is found in memory.

        Args:
            db: Database session
            show: Parent show instance
            season_key: Unique ID of the season within the show

        Returns:
            Season instance if found in memory, None otherwise

        """
        return db.identity_map.get((Season, (show.id, season_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        show: Show,
        season_key: str,
    ) -> Season:
        """Like Season.get_one but will only return a Season if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            show: Parent show instance
            season_key: Unique ID of the season within the show

        Returns:
            Season instance

        Raises:
            KeyError: If no season with the given ID exists in memory

        """
        return db.identity_map[(Season, (show.id, season_key), None)]

    def __str__(self) -> str:
        base_season = "Season: "
        if self.season_number:
            base_season += f" {self.season_number} - "
        if self.name:
            base_season += f" {self.name}"
        if self.key:
            base_season += f" ({self.key})"
        if self.id:
            base_season += f" ({self.id})"
        return f"{self.show}\n{base_season}"
