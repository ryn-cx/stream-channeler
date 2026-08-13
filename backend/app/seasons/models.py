# TODO: Validate
"""Season models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

from sqlalchemy import text
from sqlalchemy.orm import contains_eager, relationship
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    col,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.filters import is_copy
from app.canonical_media.keys import SEASON_LEVEL, tmdb_id_of
from app.models import (
    BaseMediaMixin,
    MediaMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.issue_reports.models import SeasonIssueReport

# The canonical row is the one a channel sorts on, so these name its columns and
# no copy's. A copy's own columns are only ever ordered by the admin tables, which
# order by any column they show and so are no reason to index these three.
CANONICAL_SORTABLE_FIELDS = [
    "name",
    "season_number",
    "sort_order",
]


# TODO: Validate
class BaseCanonicalSeason(BaseMediaMixin):
    """The columns a season carries, and so a copy of one carries too."""

    name: str | None = Field(default=None)
    # The season's own page, as against a copy's `url`, which is where that
    # one website streams it. TMDB's row points at themoviedb.org; a row only
    # one website knows about points wherever that website put it.
    url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)
    image_url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)


# TODO: Validate
class BaseSeason(BaseCanonicalSeason):
    """Base model for an `Season`."""


# TODO: Validate
class Season(BaseSeason, MediaMixin[Show, "Episode"], table=True):
    """Model representing a season, and a website's copy of one.

    A row is the season itself when it points at no other, and one website's
    copy of a season when it does. TMDB gives its seasons their own ids, and a
    film is filed as a season carrying the film's own number, so the key says
    the level as well as the id to keep the two apart.

    The season itself hangs off the title the way a copy hangs off the listing,
    by the same `show_id`, so one primary key covers both: a `show_id` names
    either a title or a listing and never both at once.
    """

    PARENT_ID_FIELD: ClassVar[str] = "show_id"
    CANONICAL_ID_FIELD: ClassVar[str] = "canonical_season_id"

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "random",
        "season_number_zero_last",
        "sequential",
        "sequential_zero_last",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        CANONICAL_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        Index("Season-deleted_at-index", "deleted_at"),
        Index("Season-canonical_season_id-index", "canonical_season_id"),
        *sortable_field_indexes(
            "Season",
            CANONICAL_SORTABLE_FIELDS,
            where=text("canonical_season_id IS NULL"),
        ),
    )

    # The season this is a copy of, and nothing when this is the season itself.
    # Written by whatever imports the copy rather than filled in at the flush.
    canonical_season_id: uuid.UUID = Field(
        default=None,
        nullable=True,
        foreign_key="season.id",
    )
    # `remote_side` is what says which end of the join is the season itself,
    # since both ends are the same table.
    canonical_season: Season | None = Relationship(
        sa_relationship=relationship(
            "Season",
            remote_side="Season.id",
            foreign_keys="Season.canonical_season_id",
        ),
    )

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB season this is a copy of, if TMDB has a record of it."""
        if self.canonical_season is None:
            return None
        return tmdb_id_of(self.canonical_season.key, SEASON_LEVEL)

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
        return (
            select(cls)
            .where(is_copy(cls))
            .join(Show, col(cls.show_id) == col(Show.id))
            .join(Source)
            .join(Plugin)
        )

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
        return stringify_season(self, self.show)


# TODO: Validate
def stringify_season(
    season: Season,
    parent: Show,
) -> str:
    """Return a string representation."""
    base_season = f"{type(season).__name__}:"
    if season.season_number is not None:
        base_season += f" {season.season_number} - "
    if season.name:
        base_season += f" {season.name}"
    if season.key:
        base_season += f" ({season.key})"
    if season.id:
        base_season += f" ({season.id})"
    return f"{parent}\n{base_season}"
