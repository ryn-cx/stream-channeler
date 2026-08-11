# TODO: Validate
"""Show models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

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

from app.canonical_shows.models import CanonicalShow
from app.models import (
    BaseMediaMixin,
    MediaMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.sources.models import Source
from app.users.models import User


# TODO: Validate
class BaseShow(BaseMediaMixin):
    """Base model for a `Show`."""

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    icon: str | None = Field(default=None, max_length=32)
    # Whether a `User` settled which title this is a copy of. A plugin normally
    # finds the title by searching TMDB for its name, which can land on the
    # wrong one; a lock says the answer was chosen by hand and no import may
    # replace it.
    canonical_show_locked: bool = Field(default=False)
    # How the link was arrived at, in words.
    canonical_show_note: str | None = Field(default=None)


if TYPE_CHECKING:
    from app.channels.models import ChannelSourceFilter
    from app.issue_reports.models import ShowIssueReport
    from app.seasons.models import Season


# The name "Show" was used instead of "Series" because it has a distinct singular and
# plural form and some people may use "Series" to refer to a "Season" so the word "Show"
# is less ambiguous and more flexible.
# TODO: Validate
# TODO: Validate
class Show(BaseShow, MediaMixin[Source, "Season"], table=True):
    """Model representing a `Show`."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "media_type",
        "name",
    ]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_count",
        "random",
        "started",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes(
            "Show",
            DIRECT_SORTABLE_FIELDS,
        ),
        Index("Show-deleted_at-index", "deleted_at"),
        Index("Show-canonical_show_id-index", "canonical_show_id"),
    )

    # The title this is a copy of. Never absent: `canonical_media.hooks`
    # gives a record one at the flush, before it can reach the database.
    canonical_show_id: uuid.UUID = Field(
        foreign_key="canonicalshow.id",
        ondelete="RESTRICT",
    )
    canonical_show: CanonicalShow = Relationship()

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB title this is a copy of, if TMDB has a record of it.

        Read off the canonical row rather than stored beside it, so a copy and
        the title it is of can never disagree about which TMDB record that is.
        """
        return self.canonical_show.tmdb_id if self.canonical_show else None

    source_id: uuid.UUID = Field(foreign_key="source.id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="shows")

    seasons: list[Season] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    channel_filters: list[ChannelSourceFilter] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    issue_reports: list[ShowIssueReport] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    # TODO: Validate
    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Source)
            .join(Plugin)
            .where(Source.id == self.source_id),
        ).one()

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Source).join(Plugin)

    # TODO: Validate
    @classmethod
    @override
    def select_with_user_eager(cls) -> SelectOfScalar[Self]:
        return (
            cls.select_with_plugin()
            .join(User)
            .options(
                contains_eager(cls.source)  # type: ignore[arg-type]
                .contains_eager(Source.plugin)  # type: ignore[arg-type]
                .contains_eager(Plugin.user),  # type: ignore[arg-type]
            )
        )

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Season]:
        return self.seasons

    # TODO: Validate
    @property
    @override
    def parent(self) -> Source:
        return self.source

    # TODO: Validate
    @override
    def upsert(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        parent: Source,
        existing_record: Self | None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        """Upsert the `Show`, keeping a locked the title a `User` chose intact.

        `canonical_show_locked` is only ever set by a `User`, so it is always
        protected, and while the lock is set the automatically detected
        an import works out never replaces the one the `User` chose.
        """
        protected_keys = set(protected_keys or ()) | {"canonical_show_locked"}
        if existing_record and existing_record.canonical_show_locked:
            protected_keys.add("canonical_show_id")
        return super().upsert(parent, existing_record, protected_keys)

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Show`."""
        base_show = "Show:"
        if self.name:
            base_show += f" {self.name}"
        if self.key:
            base_show += f" ({self.key})"
        if self.id:
            base_show += f" ({self.id})"
        return f"{self.source}\n{base_show}"
