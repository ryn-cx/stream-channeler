import uuid
from collections.abc import Sequence
from datetime import date
from typing import TYPE_CHECKING, Any

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

from app.models import BaseMediaMixin, MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.channels.models import ChannelEpisodeWhiteList
    from app.watches.models import Watch


class BaseEpisode(BaseMediaMixin):
    url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    name: str | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    # TODO: Test to see if these can be converted to datetimes instead of date.
    release_date: date | None = Field(default=None)
    air_date: date | None = Field(default=None)


class Episode(BaseEpisode, MediaMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        UniqueConstraint("id"),
        # Filtering options.
        Index("Episode-sort_order-index", "sort_order"),
        Index("Episode-episode_number-index", "episode_number"),
        Index("Episode-name-index", "name"),
        Index("Episode-release_date-index", "release_date"),
        Index("Episode-air_date-index", "air_date"),
        Index("Episode-duration-index", "duration"),
        # Deleted filtering.
        Index("Episode-deleted_at-index", "deleted_at"),
    )

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(back_populates="episodes")

    white_lists: list[ChannelEpisodeWhiteList] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )
    watches: list[Watch] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )

    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id)
            .select_from(Season)
            .join(Show)
            .join(Source)
            .join(Plugin)
            .where(Season.id == self.season_id),
        ).first()

    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public)
                .select_from(Season)
                .join(Show)
                .join(Source)
                .join(Plugin)
                .where(Season.id == self.season_id),
            ).first(),
        )

    def parent(self) -> Season:
        return self.season

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        season: Season,
        episode_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Episode | None:
        """Wrap `db.get(Episode, ...)` for easier use.

        Args:
            db: Database session.
            season: Parent season instance.
            episode_key: Unique ID of the episode within the season.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Episode instance if Episode is found.
            - None if no Episode is found.

        """
        return db.get(
            Episode,
            (season.id, episode_key),
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
        season: Season,
        episode_key: str,
    ) -> Episode | None:
        """Like Episode.get but will only return a Episode if it is found in memory.

        Args:
            db: Database session
            season: Parent season instance
            episode_key: Unique ID of the episode within the season

        Returns:
            Episode instance if found in memory, None otherwise

        """
        return db.identity_map.get((Episode, (season.id, episode_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        season: Season,
        episode_key: str,
    ) -> Episode:
        """Like Episode.get_one but will only return a Episode if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            season: Parent season instance
            episode_key: Unique ID of the episode within the season

        Returns:
            Episode instance

        Raises:
            KeyError: If no episode with the given ID exists in memory

        """
        return db.identity_map[(Episode, (season.id, episode_key), None)]

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        season: Season,
        episode_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Episode:
        """Wrap `db.get_one(Episode, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            season: Parent season instance.
            episode_key: Unique ID of the episode within the season.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Episode instance

        Raises:
            NoResultFound: If no episode with the given ID exists in the season

        """
        return db.get_one(
            Episode,
            (season.id, episode_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    def __str__(self) -> str:
        base_episode = "Episode: "
        if self.episode_number:
            base_episode += f" {self.episode_number} - "
        if self.name:
            base_episode += f" {self.name}"
        if self.key:
            base_episode += f" ({self.key})"
        if self.id:
            base_episode += f" ({self.id})"
        return f"{self.season}\n{base_episode}"
