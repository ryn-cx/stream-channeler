# TODO: Validate
"""Show models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, cast, override

from sqlalchemy import text
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import contains_eager, relationship
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.filters import is_copy
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
# no copy's. A copy's own columns are only ever ordered by the admin tables, which
# order by any column they show and so are no reason to index these two.
CANONICAL_SORTABLE_FIELDS = ["media_type", "name"]

# Where a session keeps its listings under the source and key naming them. A
# listing used to be found in the identity map by that pair, which was what
# named it; now that a title and a listing share a table the identity is `id`
# alone, and this is what keeps the lookup free of a query.
SHOW_SESSION_INDEX = "show_by_source_and_key"


# TODO: Validate
class BaseCanonicalShow(BaseMediaMixin):
    """The columns a title carries, and so a listing of one carries too."""

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    # What TMDB is searched under along with the name, so a title sharing its
    # name with another is still told apart. A website that does not say when
    # its titles came out leaves this empty and is matched on the name alone.
    year: int | None = Field(default=None)


# TODO: Validate
class BaseShow(BaseCanonicalShow):
    """Base model for a `Show`."""

    canonical_show_locked: bool = Field(default=False)
    canonical_show_note: str | None = Field(default=None)


# TODO: Validate
class Show(BaseShow, MediaMixin[Source, "Season"], table=True):
    """Model representing a title, and a website's listing of one.

    A row is the title itself when it points at no other, and one website's
    listing of a title when it does. The two are the same shape and are read the
    same way, so they are one table, and `canonical_show_id` is the whole of what
    tells them apart.
    """

    PARENT_ID_FIELD: ClassVar[str] = "source_id"
    CANONICAL_ID_FIELD: ClassVar[str] = "canonical_show_id"

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_count",
        "random",
        "started",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        CANONICAL_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        # A listing shares its key with the listings of other sources, so `id` is
        # the only thing that names a row of either kind on its own.
        PrimaryKeyConstraint("id"),
        # A source names each of its listings once. Written as a partial index
        # rather than a constraint because a title has no source, and a rule over
        # a column that is absent is no rule at all.
        Index(
            "Show-source_id-key-key",
            "source_id",
            "key",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
        # Every claimed title is one row, which is what makes the key the whole
        # of a title's identity. The listings are no part of this: two websites
        # carrying one title carry the same key as each other.
        Index(
            "Show-canonical-key-key",
            "key",
            unique=True,
            postgresql_where=text("canonical_show_id IS NULL"),
        ),
        Index("Show-deleted_at-index", "deleted_at"),
        Index("Show-canonical_show_id-index", "canonical_show_id"),
        *sortable_field_indexes(
            "Show",
            CANONICAL_SORTABLE_FIELDS,
            where=text("canonical_show_id IS NULL"),
        ),
    )

    # The title this is chiefly a copy of, and nothing when this is the title
    # itself. Never absent on a listing: `canonical_media.hooks` gives one at the
    # flush, before it can reach the database. A source that mixes several titles
    # into one listing is a copy of more than one, and the rest are reached
    # through `canonical_show_links`; this one is the title the copy's own name
    # and metadata belong to.
    canonical_show_id: uuid.UUID = Field(
        default=None,
        nullable=True,
        foreign_key="show.id",
    )
    # `remote_side` is what says which end of the join is the title, since both
    # ends are the same table and nothing else could tell SQLAlchemy that. Built
    # here rather than left to the annotation, which says a `Show` may stand at
    # either end and so says nothing about which of them this is.
    canonical_show: Show | None = Relationship(
        sa_relationship=relationship(
            "Show",
            remote_side="Show.id",
            foreign_keys="Show.canonical_show_id",
        ),
    )

    # Every title this is a copy of, `canonical_show_id` among them. A website
    # that files two titles under one listing - a YouTube channel whose uploads
    # are two series, a service that sells a sequel as another season - is a copy
    # of each of them, and nothing about it says which of the two a caller means.
    canonical_show_links: list[ShowCanonicalShow] = Relationship(
        back_populates="show",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "ShowCanonicalShow.show_id"},
    )

    # TODO: Validate
    @property
    def canonical_shows(self) -> list[Show]:
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

    # The website this is a listing on, and nothing when this is the title
    # itself: a title is not carried anywhere, it is what the carrying is of.
    source_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="source.id",
        ondelete="CASCADE",
    )
    # Typed as always there because every caller that reaches for it holds a
    # listing. A title has none, and reading it off one is the mistake `parent`
    # is there to name.
    source: Source = Relationship(back_populates="shows")

    # A listing's own seasons, and a title's own seasons, by the same column: a
    # canonical season hangs off the title the way a copy hangs off the listing.
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
        # The join to `Source` already leaves the titles out, since a title has
        # none. Said out loud anyway: what this returns is the listings, and a
        # read that means them should not rest on a join to say so.
        return select(cls).where(is_copy(cls)).join(Source).join(Plugin)

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
    @classmethod
    @override
    def get_from_memory(
        cls,
        session: Session,
        parent: Source,
        key: str,
    ) -> Self | None:
        """Return the listing `parent` names under `key`, without a query.

        The identity map answers to `id` now that a title and a listing share a
        table, so the pair is looked for in the session's own index of it
        instead. A row the session has since let go of is not one it holds, and
        is answered for as though it had never been indexed.
        """
        show = show_session_index(session).get((parent.id, key))
        if show is None or show not in session:
            return None
        return cast("Self", show)

    # TODO: Validate
    @classmethod
    @override
    def get_one_from_memory(
        cls,
        session: Session,
        parent: Source,
        key: str,
    ) -> Self:
        """Return the listing `parent` names under `key`, raising if it holds none.

        Raises:
            KeyError: If the session is holding no such listing.

        """
        show = cls.get_from_memory(session, parent, key)
        if show is None:
            raise KeyError((cls, (parent.id, key)))
        return show

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Season]:
        return self.seasons

    # TODO: Validate
    @property
    @override
    def parent(self) -> Source:
        # A title is on no website, so asking a title what it is carried on is
        # asking the wrong row, and saying so here is what keeps that from
        # turning into a missing owner somewhere further along.
        if self.source_id is None:
            msg = f"{self} is a title rather than a listing, so it has no source"
            raise ValueError(msg)
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
def show_session_index(
    session: SQLAlchemySession,
) -> dict[tuple[uuid.UUID, str], Show]:
    """Return the session's index of the listings it is holding."""
    index: dict[tuple[uuid.UUID, str], Show] = session.info.setdefault(
        SHOW_SESSION_INDEX,
        {},
    )
    return index


# TODO: Validate
def index_show(session: SQLAlchemySession, show: Show) -> None:
    """Record `show` under the source and key naming it.

    The source is read off the column first and off the relationship only where
    the column has yet to be written, so a stored row costs nothing to index.
    The relationship is read out of what is already loaded rather than through
    the attribute, which on a title would go and fetch the source it has none
    of. A title is not indexed at all: it is not on a website and nothing looks
    one up this way.
    """
    source_id = show.source_id
    if source_id is None:
        source = show.__dict__.get("source")
        source_id = source.id if source is not None else None
    if source_id is not None:
        show_session_index(session)[(source_id, show.key)] = show


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
    """Base model for one of the titles a `Show` is a copy of."""

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    canonical_show_id: uuid.UUID = Field(
        foreign_key="show.id",
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

    # Both ends are a `Show`, so which foreign key each relationship follows has
    # to be named; nothing about the columns says which of them is the listing.
    show: Show = Relationship(
        back_populates="canonical_show_links",
        sa_relationship_kwargs={"foreign_keys": "ShowCanonicalShow.show_id"},
    )
    canonical_show: Show = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "ShowCanonicalShow.canonical_show_id",
        },
    )
