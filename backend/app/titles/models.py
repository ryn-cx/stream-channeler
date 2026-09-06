# TODO: Validate
"""Title models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Self, override

from sqlalchemy import text
from sqlalchemy.orm import contains_eager, selectinload
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
    UniqueConstraint,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.tmdb import (
    get_tmdb_id,
)
from app.models import (
    BaseMediaMixin,
    ChildMediaMixin,
    DateTimeField,
    TimestampIdAndHashMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.sources.models import Source

if TYPE_CHECKING:
    from app.channels.models import ChannelSourceFilter
    from app.issue_reports.models import TitleIssueReport
    from app.seasons.models import Season

# The canonical row is the one a channel sorts on, so these name its columns and no
# non-canonical row's. Those are only ever ordered by the admin tables, which order by
# any column they show and so are no reason to index these two.
CANONICAL_SORTABLE_FIELDS = ["media_type", "name"]


# TODO: Validate
class BaseCanonicalTitle(BaseMediaMixin):
    """The columns a canonical title carries, and so a non-canonical one too."""

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    thumbnail_url: str | None = Field(default=None)
    # What TMDB is searched under along with the name, so a title sharing its
    # name with another is still told apart. A website that does not say when
    # its titles came out leaves this empty and is matched on the name alone.
    year: int | None = Field(default=None)


# TODO: Validate
class BaseTitle(BaseCanonicalTitle):
    """Base model for a `Title`."""

    canonical_title_validated_at: datetime | None = DateTimeField(default=None)


# TODO: Validate
class Title(BaseTitle, ChildMediaMixin[Source, "Season"], table=True):
    """Model representing a title."""

    PARENT_ID_FIELD: ClassVar[str] = "source_id"
    CANONICAL_FLAG_FIELD: ClassVar[str] = "is_canonical"

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_count",
        "random",
        "started",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        CANONICAL_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        # A source names each of its rows once, of either kind: a canonical title is
        # written by the plugin that minted it the same way a non-canonical row is
        # written by the plugin that read it off a website, and the two never share a
        # key under one source. A canonical title minted for a listing to point at
        # carries the plugin's key ahead of the listing's, and TMDB writes canonical
        # titles and nothing else. That pair is the identity `Season` and `Episode` carry
        # too, so the identity map answers to it and `get_from_memory` needs nothing of
        # its own.
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        # Looking a canonical title up by its key. Not unique: a plugin that
        # offers one title through several sources writes a row per source under
        # the same key, and every one of them is canonical until TMDB matches it.
        Index(
            "Title-canonical-key-index",
            "key",
            postgresql_where=text("is_canonical IS TRUE"),
        ),
        Index("Title-deleted_at-index", "deleted_at"),
        Index("Title-is_canonical-index", "is_canonical"),
        *sortable_field_indexes(
            "Title",
            CANONICAL_SORTABLE_FIELDS,
            where=text("is_canonical IS TRUE"),
        ),
    )

    # Whether this row is the title itself rather than one website's row standing for it.
    # Which canonical titles a non-canonical row stands for is stored in
    # `TitleCanonicalTitle` and nowhere else, since a website that files two titles under
    # one page - a YouTube channel whose uploads are two series, a service that sells a
    # sequel as another season - stands for each of them equally, and a column could
    # only hold one.
    is_canonical: bool = Field(default=True)

    # Every canonical title this stands for. Nothing about a non-canonical row says which
    # of them a caller with room for one means, so nothing here puts one ahead of
    # another.
    canonical_title_links: list[TitleCanonicalTitle] = Relationship(
        back_populates="non_canonical_title",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "TitleCanonicalTitle.title_id"},
    )

    # The other end of the same table: every non-canonical row standing for this one,
    # which only a canonical title ever has. A row with both stands for something and is
    # stood for by something, which is the one shape the levels never take.
    non_canonical_title_links: list[TitleCanonicalTitle] = Relationship(
        back_populates="canonical_title",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "TitleCanonicalTitle.canonical_title_id",
        },
    )

    # TODO: Validate
    @property
    def canonical_titles(self) -> list[Title]:
        """Every canonical title this stands for, in the order they were linked."""
        return [link.canonical_title for link in self.canonical_title_links]

    # TODO: Validate
    @property
    def canonical_title_ids(self) -> list[uuid.UUID]:
        """The id of every canonical title this stands for.

        Read off the links rather than off the titles they point at, since the id
        is a column of the link itself and reading the titles to ask them their
        own ids is a query per link for something already in hand.
        """
        return [link.canonical_title_id for link in self.canonical_title_links]

    # TODO: Validate
    @property
    def sole_canonical_title(self) -> Title | None:
        """The canonical title this stands for, where it stands for exactly one.

        A row that mixes titles stands for each of them as much as for any other,
        so there is no answer to give a caller with room for one and it is told
        there is none rather than handed whichever came first.
        """
        canonical_titles = self.canonical_titles
        if len(canonical_titles) != 1:
            return None
        return canonical_titles[0]

    # TODO: Validate
    @property
    def sole_canonical_title_id(self) -> uuid.UUID | None:
        """The id of the canonical title this stands for, where there is one."""
        canonical_title = self.sole_canonical_title
        return canonical_title.id if canonical_title else None

    # TODO: Validate
    @property
    def tmdb_ids(self) -> list[int]:
        return [
            get_tmdb_id(canonical_title.key)
            for canonical_title in self.canonical_titles
        ]

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB id of the canonical title this stands for, where there is one.

        Read out of the canonical row's key rather than stored beside it, so a
        non-canonical row and the row it stands for can never disagree about which TMDB
        record that is.
        """
        canonical_title = self.sole_canonical_title
        if canonical_title is None:
            return None
        return get_tmdb_id(canonical_title.key)

    # What wrote this row. A non-canonical row has the website it was read off, and a
    # canonical title has the plugin that minted it, which is TMDB wherever TMDB has a
    # record of the title and the reading plugin itself where nothing catalogued it.
    # Either way a row was written by something, so this is never absent and neither
    # kind of row is told from the other by it.
    source_id: uuid.UUID = Field(foreign_key="source.id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="titles")

    # The seasons of either kind of row, by the same column: a canonical season hangs
    # off a canonical title the way a non-canonical season hangs off a non-canonical one.
    seasons: list[Season] = Relationship(
        back_populates="title",
        cascade_delete=True,
    )

    channel_filters: list[ChannelSourceFilter] = Relationship(
        back_populates="title",
        cascade_delete=True,
    )

    issue_reports: list[TitleIssueReport] = Relationship(
        back_populates="title",
        cascade_delete=True,
    )

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        # Every row has a source and is listed under it, whether it is the record of the
        # media or a non-canonical row of one. A row is not hidden for being the record:
        # that is what a title nothing else catalogued looks like, and it is where the
        # media is watched.
        return select(cls).join(Source).join(Plugin)

    # TODO: Validate
    @classmethod
    def select_with_plugin_eager(cls) -> SelectOfScalar[Self]:
        return cls.select_with_plugin().options(
            contains_eager(cls.source).contains_eager(Source.plugin),  # type: ignore[arg-type]  # type: ignore[arg-type]
            # Which canonical titles a row stands for is read off every row
            # that is served, and it is a table away now rather than a column
            # of the row, so it is fetched with them rather than one at a
            # time.
            selectinload(cls.canonical_title_links),  # type: ignore[arg-type]
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
        """Upsert the `Title`, keeping the canonical title a `User` chose intact.

        `canonical_title_locked` is only ever set by a `User`, so it is always
        protected. The canonical titles themselves are rows of `TitleCanonicalTitle`
        rather than a column of this one, so an upsert cannot write them away and
        what honours the lock is whatever would go on to link them. `is_canonical`
        is protected with them: a record built fresh off a website's files knows
        nothing of the links the stored row already carries, and a row that kept
        its links while being called canonical again would be stood for by other
        rows and standing for some itself.
        """
        protected_keys = set(protected_keys or ()) | {
            "canonical_title_validated_at",
            "is_canonical",
        }
        return super().upsert(parent, existing_record, protected_keys)

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Title`."""
        return stringify_title(self, self.source)


# TODO: Validate
def stringify_title(title: Title, parent: Source | None) -> str:
    """Return a string representation."""
    base_title = f"{type(title).__name__}:"
    if title.name:
        base_title += f" {title.name}"
    if title.key:
        base_title += f" ({title.key})"
    if title.id:
        base_title += f" ({title.id})"
    if parent is None:
        return base_title
    return f"{parent}\n{base_title}"


# TODO: Validate
class BaseTitleCanonicalTitle(SQLModel):
    """Base model for one of the canonical titles a `Title` stands for."""

    title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    canonical_title_id: uuid.UUID = Field(
        foreign_key="title.id",
        ondelete="CASCADE",
    )
    note: str | None = Field(default=None)


# TODO: Validate
class TitleCanonicalTitle(BaseTitleCanonicalTitle, TimestampIdAndHashMixin, table=True):
    """Model representing one of the canonical titles a `Title` stands for.

    A website's row stands for one canonical title in the ordinary case and for
    several where the website mixes them, and there is nothing on the row that
    tells the two apart, so which ones it stands for is stored rather than
    inferred. This is the whole of that record: every canonical title a row stands
    for has a row here and none of them is held anywhere else, so a query asking
    which rows stand for a canonical title asks one table and no other.
    """

    __table_args__ = (
        # Each canonical title is linked to a non-canonical row at most once; the leading
        # column also serves lookups of a row's canonical titles and cascade deletion
        # with it.
        PrimaryKeyConstraint("title_id", "canonical_title_id"),
        # Used to find every non-canonical row standing for a canonical title.
        Index("TitleCanonicalTitle-canonical_title_id-index", "canonical_title_id"),
    )

    # Both ends are a `Title`, so which foreign key each relationship follows has
    # to be named; nothing about the columns says which of them is which.
    non_canonical_title: Title = Relationship(
        back_populates="canonical_title_links",
        sa_relationship_kwargs={"foreign_keys": "TitleCanonicalTitle.title_id"},
    )
    canonical_title: Title = Relationship(
        back_populates="non_canonical_title_links",
        sa_relationship_kwargs={
            "foreign_keys": "TitleCanonicalTitle.canonical_title_id",
        },
    )
