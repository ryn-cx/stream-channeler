# TODO: Validate
"""Season models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

from pydantic import computed_field
from sqlalchemy.orm import contains_eager
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
    text,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.media.identifiers import identifier_tmdb_id
from app.models import (
    BaseMediaMixin,
    MediaMixin,
    placeholder_identifier,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.issue_reports.models import SeasonIssueReport


# TODO: Validate
class BaseSeason(BaseMediaMixin):
    """Base model for an `Season`."""

    sort_order: int | None = Field(default=None)
    name: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)
    # What makes the same season on two websites one season rather than two. It
    # is the TMDB id whenever the season is linked to TMDB, and the plugin's own
    # key for the season when it is not.
    season_identifier: str

    # TODO: Validate
    @computed_field
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB season `season_identifier` names, if it names one.

        Read off the identifier rather than stored beside it, so the two can
        never disagree about which TMDB record this is.
        """
        return identifier_tmdb_id(self.season_identifier)


# TODO: Validate
class Season(BaseSeason, MediaMixin[Show, "Episode"], table=True):
    """Model representing a `Season`."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "name",
        "season_identifier",
        "season_number",
        "sort_order",
    ]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "random",
        "season_number_zero_last",
        "sequential",
        "sequential_zero_last",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes(
            "Season",
            DIRECT_SORTABLE_FIELDS,
            already_indexed=("season_identifier",),
        ),
        Index("Season-deleted_at-index", "deleted_at"),
        Index("Season-season_identifier-index", "season_identifier", "id"),
        Index(
            "Season-live-season_identifier-index",
            "season_identifier",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # Named after the plugin that read the record by `_merge_and_upsert_*`,
    # and after the TMDB season behind it when there is one, so it is not
    # something the record has to be built with.
    season_identifier: str = Field(default_factory=placeholder_identifier)

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(back_populates="seasons")

    episodes: list[Episode] = Relationship(back_populates="season", cascade_delete=True)

    issue_reports: list[SeasonIssueReport] = Relationship(
        back_populates="season",
        cascade_delete=True,
    )

    # TODO: Validate
    @property
    @override
    def parent(self) -> Show:
        return self.show

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Episode]:
        return self.episodes

    # TODO: Validate
    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Show)
            .join(Source)
            .join(Plugin)
            .where(Show.id == self.show_id),
        ).one()

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Show).join(Source).join(Plugin)

    # TODO: Validate
    @classmethod
    @override
    def select_with_user_eager(cls) -> SelectOfScalar[Self]:
        return (
            cls.select_with_plugin()
            .join(User)
            .options(
                contains_eager(cls.show)  # type: ignore[arg-type]
                .contains_eager(Show.source)  # type: ignore[arg-type]
                .contains_eager(Source.plugin)  # type: ignore[arg-type]
                .contains_eager(Plugin.user),  # type: ignore[arg-type]
            )
        )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Season`."""
        base_season = "Season:"
        if self.season_number:
            base_season += f" {self.season_number} - "
        if self.name:
            base_season += f" {self.name}"
        if self.key:
            base_season += f" ({self.key})"
        if self.id:
            base_season += f" ({self.id})"
        return f"{self.show}\n{base_season}"
