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
    SQLModel,
    UniqueConstraint,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.keys import SHOW_LEVEL, tmdb_id_of
from app.models import (
    BaseMediaMixin,
    MediaMixin,
    TimestampIdAndHashMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.sources.models import Source
from app.users.models import User

if TYPE_CHECKING:
    from app.channels.models import ChannelSourceFilter
    from app.issue_reports.models import ShowIssueReport
    from app.seasons.models import CanonicalSeason, Season

# The canonical row is the one a channel sorts on, so these name its columns and
# no copy's. A copy's own columns are only ever ordered by the admin tables, which
# order by any column they show and so are no reason to index these two.
CANONICAL_SORTABLE_FIELDS = ["media_type", "name"]


# TODO: Validate
class BaseCanonicalShow(BaseMediaMixin):
    """Base model for `CanonicalShow` and `Show` models."""

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


# TODO: Validate
class BaseShow(BaseCanonicalShow):
    """Base model for a `Show`."""

    canonical_show_locked: bool = Field(default=False)
    canonical_show_note: str | None = Field(default=None)


# TODO: Validate
class CanonicalShow(TimestampIdAndHashMixin, BaseCanonicalShow, table=True):
    """Model representing a canonical show."""

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_count",
        "random",
        "started",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        CANONICAL_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Postgres counts NULLs as distinct, so this binds every claimed title
        # to one row while leaving titles nothing has claimed free to be as many
        # rows as there are of them.
        UniqueConstraint("key", name="CanonicalShow-key-key"),
        *sortable_field_indexes("CanonicalShow", CANONICAL_SORTABLE_FIELDS),
    )

    canonical_seasons: list[CanonicalSeason] = Relationship(
        back_populates="canonical_show",
        cascade_delete=True,
    )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `CanonicalShow`."""
        return stringify_show(self, None)


# TODO: Validate
class Show(BaseShow, MediaMixin[Source, "Season"], table=True):
    """Model representing a `Show`."""

    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        Index("Show-deleted_at-index", "deleted_at"),
        Index("Show-canonical_show_id-index", "canonical_show_id"),
    )

    # The title this is chiefly a copy of. Never absent: `canonical_media.hooks`
    # gives a record one at the flush, before it can reach the database. A source
    # that mixes several titles into one listing is a copy of more than one, and
    # the rest are reached through `canonical_show_links`; this one is the title
    # the copy's own name and metadata belong to.
    canonical_show_id: uuid.UUID = Field(
        foreign_key="canonicalshow.id",
        ondelete="RESTRICT",
    )
    canonical_show: CanonicalShow = Relationship()

    # Every title this is a copy of, `canonical_show_id` among them. A website
    # that files two titles under one listing - a YouTube channel whose uploads
    # are two series, a service that sells a sequel as another season - is a copy
    # of each of them, and nothing about it says which of the two a caller means.
    canonical_show_links: list[ShowCanonicalShow] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    # TODO: Validate
    @property
    def canonical_shows(self) -> list[CanonicalShow]:
        """Every title this is a copy of, the one it is chiefly a copy of first.

        The chief title leads because it is the one a caller with only one title
        to work with means, and the rest follow in the order they were linked.
        """
        linked = [
            link.canonical_show
            for link in self.canonical_show_links
            if link.canonical_show_id != self.canonical_show_id
        ]
        return [self.canonical_show, *linked] if self.canonical_show else linked

    # TODO: Validate
    @property
    def canonical_show_ids(self) -> list[uuid.UUID]:
        """The id of every title this is a copy of, the chief one first."""
        return [canonical_show.id for canonical_show in self.canonical_shows]

    # TODO: Validate
    @property
    def tmdb_ids(self) -> list[int]:
        """The TMDB title behind each title this is a copy of, where there is one."""
        return [
            tmdb_id
            for canonical_show in self.canonical_shows
            if (tmdb_id := tmdb_id_of(canonical_show.key, SHOW_LEVEL)) is not None
        ]

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB title this is a copy of, if TMDB has a record of it.

        Read out of the canonical row's key rather than stored beside it, so a
        copy and the title it is of can never disagree about which TMDB record
        that is.
        """
        if self.canonical_show is None:
            return None
        return tmdb_id_of(self.canonical_show.key, SHOW_LEVEL)

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
        return stringify_show(self, self.source)


# TODO: Validate
def stringify_show(show: Show | CanonicalShow, parent: Source | None) -> str:
    """Return a string representation."""
    base_show = f"{type(show).__name__}:"
    if show.name:
        base_show += f" {show.name}"
    if show.key:
        base_show += f" ({show.key})"
    if show.id:
        base_show += f" ({show.id})"
    if parent is None:
        return base_show
    return f"{parent}\n{base_show}"


# TODO: Validate
class BaseShowCanonicalShow(SQLModel):
    """Base model for one of the titles a `Show` is a copy of."""

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    canonical_show_id: uuid.UUID = Field(
        foreign_key="canonicalshow.id",
        ondelete="CASCADE",
    )


# TODO: Validate
class ShowCanonicalShow(BaseShowCanonicalShow, TimestampIdAndHashMixin, table=True):
    """Model representing one of the titles a `Show` is a copy of.

    A website's listing is a copy of one title in the ordinary case and of
    several where the website mixes them, and there is nothing on the listing
    that tells the two apart, so which titles it is of is stored rather than
    inferred. `Show.canonical_show_id` is among them: the chief title has a row
    here like any other, so a query asking which copies stand for a title can ask
    one table and get the same answer either way.
    """

    __table_args__ = (
        # Each title is linked to a copy at most once; the leading column also
        # serves lookups of a copy's titles and cascade deletion with the copy.
        PrimaryKeyConstraint("show_id", "canonical_show_id"),
        # Used to find every copy standing for a title.
        Index("ShowCanonicalShow-canonical_show_id-index", "canonical_show_id"),
    )

    show: Show = Relationship(back_populates="canonical_show_links")
    canonical_show: CanonicalShow = Relationship()
