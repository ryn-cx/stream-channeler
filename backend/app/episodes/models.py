# TODO: Validate
"""Episode models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Never, Self, override

from sqlalchemy.orm import contains_eager
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.models import BaseMediaMixin, DateTimeField, MediaMixin, sortable_field_indexes
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

if TYPE_CHECKING:
    from app.watches.models import Watch


class BaseEpisode(BaseMediaMixin):
    """Base model for an `Episode`."""

    url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    name: str | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    release_date: datetime | None = DateTimeField(default=None)
    air_date: datetime | None = DateTimeField(default=None)
    tmdb_id: int | None = Field(default=None)
    episode_identifier: str
    episode_identifier_locked: bool = Field(default=False)
    # What a `User` says is wrong with the episode, which is about the episode
    # rather than about what any website reported, so an import never clears it.
    issue_report: str | None = Field(default=None)


class Episode(BaseEpisode, MediaMixin[Season, Never], table=True):
    """Model representing an episode."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "air_date",
        "duration",
        "episode_identifier",
        "episode_number",
        "id",
        "name",
        "release_date",
        "sort_order",
    ]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_number_zero_last",
        "last_watched_completed",
        "last_watched_incomplete",
        "random",
        "recently_aired",
        "saved_order",
        "sequential",
        "sequential_zero_last",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes(
            "Episode",
            DIRECT_SORTABLE_FIELDS,
            already_indexed=("episode_identifier",),
        ),
        Index("Episode-deleted_at-index", "deleted_at"),
        Index("Episode-episode_identifier-index", "episode_identifier", "id"),
    )

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(back_populates="episodes")

    # Deleting an episode leaves its watches behind, detached, rather than
    # taking them with it. `passive_deletes` hands that to the database's
    # `ON DELETE SET NULL` instead of SQLAlchemy nulling each row itself.
    watches: list[Watch] = Relationship(
        back_populates="episode",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Season)
            .join(Show)
            .join(Source)
            .join(Plugin)
            .where(Season.id == self.season_id),
        ).one()

    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Season).join(Show).join(Source).join(Plugin)

    @classmethod
    @override
    def select_with_user_eager(cls) -> SelectOfScalar[Self]:
        return (
            cls.select_with_plugin()
            .join(User)
            .options(
                contains_eager(cls.season)  # type: ignore[arg-type]
                .contains_eager(Season.show)  # type: ignore[arg-type]
                .contains_eager(Show.source)  # type: ignore[arg-type]
                .contains_eager(Source.plugin)  # type: ignore[arg-type]
                .contains_eager(Plugin.user),  # type: ignore[arg-type]
            )
        )

    @property
    @override
    def parent(self) -> Season:
        return self.season

    @property
    @override
    def children(self) -> list[Never]:
        return []

    @override
    def upsert(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        parent: Season,
        existing_record: Self | None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        """Upsert the `Episode`, keeping a locked `episode_identifier` intact.

        `episode_identifier_locked` and `issue_report` are only ever set by a
        `User`, so they are always protected, and while the lock is set the
        automatically detected `episode_identifier` never replaces the one the
        `User` chose.
        """
        protected_keys = set(protected_keys or ()) | {
            "episode_identifier_locked",
            "issue_report",
        }
        if existing_record and existing_record.episode_identifier_locked:
            protected_keys.add("episode_identifier")
        return super().upsert(parent, existing_record, protected_keys)

    def __str__(self) -> str:
        """Return a string representation of the `Episode`."""
        base_episode = "Episode:"
        if self.episode_number:
            base_episode += f" {self.episode_number} - "
        if self.name:
            base_episode += f" {self.name}"
        if self.key:
            base_episode += f" ({self.key})"
        if self.id:
            base_episode += f" ({self.id})"
        return f"{self.season}\n{base_episode}"
