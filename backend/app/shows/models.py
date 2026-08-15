# TODO: Validate
"""Show models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

from sqlalchemy import text
from sqlalchemy.orm import contains_eager, selectinload
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
    from app.seasons.models import Season

# The canonical row is the one a channel sorts on, so these name its columns and
# no non-canonical row's. Those are only ever ordered by the admin tables, which
# order by any column they show and so are no reason to index these two.
CANONICAL_SORTABLE_FIELDS = ["media_type", "name"]


# TODO: Validate
class BaseCanonicalShow(BaseMediaMixin):
    """The columns a canonical show carries, and so a non-canonical one too."""

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    # What TMDB is searched under along with the name, so a show sharing its
    # name with another is still told apart. A website that does not say when
    # its shows came out leaves this empty and is matched on the name alone.
    year: int | None = Field(default=None)


# TODO: Validate
class BaseShow(BaseCanonicalShow):
    """Base model for a `Show`."""

    canonical_show_locked: bool = Field(default=False)
    canonical_show_note: str | None = Field(default=None)


# TODO: Validate
class Show(BaseShow, MediaMixin[Source, "Season"], table=True):
    """Model representing a show, canonical or not.

    A row is the canonical show itself, or one website's non-canonical row
    standing for however many canonical shows that website mixed into it. The two
    are the same shape and are read the same way, so they are one table, and
    `is_canonical` is the whole of what tells them apart. Which canonical shows a
    non-canonical row stands for is stored in `ShowCanonicalShow` alone, where no
    one of them stands above the rest.
    """

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
        # A source names each of its rows once, of either kind: a canonical show
        # is written by the plugin that minted it the same way a non-canonical
        # row is written by the plugin that read it off a website, and the two
        # never share a key under one source. A canonical show minted for a
        # listing to point at carries the plugin's key ahead of the listing's,
        # and TMDB writes canonical shows and nothing else. That pair is the
        # identity `Season` and `Episode` carry too, so the identity map answers
        # to it and `get_from_memory` needs nothing of its own.
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        # Every claimed canonical show is one row, which is what makes the key
        # the whole of its identity. The non-canonical rows are no part of this:
        # two websites carrying one show carry the same key as each other.
        Index(
            "Show-canonical-key-key",
            "key",
            unique=True,
            postgresql_where=text("is_canonical IS TRUE"),
        ),
        Index("Show-deleted_at-index", "deleted_at"),
        Index("Show-is_canonical-index", "is_canonical"),
        *sortable_field_indexes(
            "Show",
            CANONICAL_SORTABLE_FIELDS,
            where=text("is_canonical IS TRUE"),
        ),
    )

    # Whether this row is the show itself rather than one website's row standing
    # for it. Which canonical shows a non-canonical row stands for is stored in
    # `ShowCanonicalShow` and nowhere else, since a website that files two shows
    # under one page - a YouTube channel whose uploads are two series, a service
    # that sells a sequel as another season - stands for each of them equally,
    # and a column could only hold one.
    is_canonical: bool = Field(default=True)

    # Every canonical show this stands for. Nothing about a non-canonical row
    # says which of them a caller with room for one means, so nothing here puts
    # one ahead of another.
    canonical_show_links: list[ShowCanonicalShow] = Relationship(
        back_populates="show",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "ShowCanonicalShow.show_id"},
    )

    # The other end of the same table: every non-canonical row standing for this
    # one, which only a canonical show ever has. A row with both stands for
    # something and is stood for by something, which is the one shape the levels
    # never take.
    non_canonical_shows: list[ShowCanonicalShow] = Relationship(
        back_populates="canonical_show",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "ShowCanonicalShow.canonical_show_id",
        },
    )

    # TODO: Validate
    @property
    def canonical_shows(self) -> list[Show]:
        """Every canonical show this stands for, in the order they were linked."""
        return [link.canonical_show for link in self.canonical_show_links]

    # TODO: Validate
    @property
    def canonical_show_ids(self) -> list[uuid.UUID]:
        """The id of every canonical show this stands for."""
        return [canonical_show.id for canonical_show in self.canonical_shows]

    # TODO: Validate
    @property
    def sole_canonical_show(self) -> Show | None:
        """The canonical show this stands for, where it stands for exactly one.

        A row that mixes shows stands for each of them as much as for any other,
        so there is no answer to give a caller with room for one and it is told
        there is none rather than handed whichever came first.
        """
        canonical_shows = self.canonical_shows
        if len(canonical_shows) != 1:
            return None
        return canonical_shows[0]

    # TODO: Validate
    @property
    def sole_canonical_show_id(self) -> uuid.UUID | None:
        """The id of the canonical show this stands for, where there is one."""
        canonical_show = self.sole_canonical_show
        return canonical_show.id if canonical_show else None

    # TODO: Validate
    @property
    def tmdb_ids(self) -> list[int]:
        """The TMDB id behind each canonical show this stands for, where it has one."""
        return [
            tmdb_id
            for canonical_show in self.canonical_shows
            if (tmdb_id := tmdb_id_of(canonical_show.key, SHOW_LEVEL)) is not None
        ]

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB id of the canonical show this stands for, where there is one.

        Read out of the canonical row's key rather than stored beside it, so a
        non-canonical row and the row it stands for can never disagree about
        which TMDB record that is.
        """
        canonical_show = self.sole_canonical_show
        if canonical_show is None:
            return None
        return tmdb_id_of(canonical_show.key, SHOW_LEVEL)

    # What wrote this row. A non-canonical row has the website it was read off,
    # and a canonical show has the plugin that minted it, which is TMDB wherever
    # TMDB has a record of the title and the reading plugin itself where nothing
    # catalogued it. Either way a row was written by something, so this is never
    # absent and neither kind of row is told from the other by it.
    source_id: uuid.UUID = Field(foreign_key="source.id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="shows")

    # The seasons of either kind of row, by the same column: a canonical season
    # hangs off a canonical show the way a non-canonical season hangs off a
    # non-canonical one.
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
        # Every row has a source and is listed under it, whether it is the record
        # of the media or a copy of one. A row is not hidden for being the record:
        # that is what a title nothing else catalogued looks like, and it is where
        # the media is watched.
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
                .contains_eager(Plugin.user),
                # Which canonical shows a row stands for is read off every row
                # that is served, and it is a table away now rather than a column
                # of the row, so it is fetched with them rather than one at a
                # time.
                selectinload(cls.canonical_show_links),  # type: ignore[arg-type]
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
        """Upsert the `Show`, keeping the canonical show a `User` chose intact.

        `canonical_show_locked` is only ever set by a `User`, so it is always
        protected. The canonical shows themselves are rows of `ShowCanonicalShow`
        rather than a column of this one, so an upsert cannot write them away and
        what honours the lock is whatever would go on to link them. `is_canonical`
        is protected with them: a record built fresh off a website's files knows
        nothing of the links the stored row already carries, and a row that kept
        its links while being called canonical again would be stood for by other
        rows and standing for some itself.
        """
        protected_keys = set(protected_keys or ()) | {
            "canonical_show_locked",
            "is_canonical",
        }
        return super().upsert(parent, existing_record, protected_keys)

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Show`."""
        return stringify_show(self, self.source)


# TODO: Validate
def stringify_show(show: Show, parent: Source | None) -> str:
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
    """Base model for one of the canonical shows a `Show` stands for."""

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    canonical_show_id: uuid.UUID = Field(
        foreign_key="show.id",
        ondelete="CASCADE",
    )


# TODO: Validate
class ShowCanonicalShow(BaseShowCanonicalShow, TimestampIdAndHashMixin, table=True):
    """Model representing one of the canonical shows a `Show` stands for.

    A website's row stands for one canonical show in the ordinary case and for
    several where the website mixes them, and there is nothing on the row that
    tells the two apart, so which ones it stands for is stored rather than
    inferred. This is the whole of that record: every canonical show a row stands
    for has a row here and none of them is held anywhere else, so a query asking
    which rows stand for a canonical show asks one table and no other.
    """

    __table_args__ = (
        # Each canonical show is linked to a non-canonical row at most once; the
        # leading column also serves lookups of a row's canonical shows and
        # cascade deletion with it.
        PrimaryKeyConstraint("show_id", "canonical_show_id"),
        # Used to find every non-canonical row standing for a canonical show.
        Index("ShowCanonicalShow-canonical_show_id-index", "canonical_show_id"),
    )

    # Both ends are a `Show`, so which foreign key each relationship follows has
    # to be named; nothing about the columns says which of them is which.
    show: Show = Relationship(
        back_populates="canonical_show_links",
        sa_relationship_kwargs={"foreign_keys": "ShowCanonicalShow.show_id"},
    )
    canonical_show: Show = Relationship(
        back_populates="non_canonical_shows",
        sa_relationship_kwargs={
            "foreign_keys": "ShowCanonicalShow.canonical_show_id",
        },
    )
