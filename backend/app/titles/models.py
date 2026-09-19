# TODO: Validate
"""Title models."""

import uuid
from collections.abc import Iterable, Mapping
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

from app.models import (
    BaseMediaMixin,
    ChildMediaMixin,
    DateTimeField,
    TimestampIdAndHashMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.sources.models import Source
from app.tmdb_media.tmdb import (
    get_tmdb_id,
)
from app.watch_providers.models import WatchProvider

if TYPE_CHECKING:
    from app.channels.models import ChannelSourceFilter
    from app.issue_reports.models import TitleIssueReport
    from app.seasons.models import Season

# The canonical row is the one a channel sorts on, so these name its columns and no
# non-canonical row's. Those are only ever ordered by the admin tables, which order by
# any column they show and so are no reason to index these two.
TMDB_SORTABLE_FIELDS = ["media_type", "name"]


# TODO: Validate
class BaseTmdbTitle(BaseMediaMixin):
    """The columns a canonical title carries, and so a non-canonical one too."""

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    thumbnail_url: str | None = Field(default=None)
    poster_url: str | None = Field(default=None)
    poster_thumbnail_url: str | None = Field(default=None)
    # What TMDB is searched under along with the name, so a title sharing its
    # name with another is still told apart. A website that does not say when
    # its titles came out leaves this empty and is matched on the name alone.
    year: int | None = Field(default=None)
    score: float | None = Field(default=None)
    popularity: float | None = Field(default=None)
    original_language: str | None = Field(default=None)


# TODO: Validate
class BaseTitle(BaseTmdbTitle):
    """Base model for a `Title`."""

    tmdb_title_validated_at: datetime | None = DateTimeField(default=None)


# TODO: Validate
class Title(BaseTitle, ChildMediaMixin[Source, "Season"], table=True):
    """Model representing a title."""

    PARENT_ID_FIELD: ClassVar[str] = "source_id"
    LINKED_FLAG_FIELD: ClassVar[str] = "is_linked"

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_count",
        "random",
        "started",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        TMDB_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        # Looking a canonical title up by its key. Not unique: a plugin that
        # offers one title through several sources writes a row per source under
        # the same key, and every one of them is canonical until TMDB matches it.
        Index(
            "Title-unlinked-key-index",
            "key",
            postgresql_where=text("is_linked IS FALSE"),
        ),
        Index("Title-deleted_at-index", "deleted_at"),
        Index("Title-is_linked-index", "is_linked"),
        Index(
            "Title-link_status-index",
            "link_status",
            postgresql_where=text("link_status IS NULL"),
        ),
        *sortable_field_indexes(
            "Title",
            TMDB_SORTABLE_FIELDS,
            where=text("is_linked IS FALSE"),
        ),
    )

    link_status: str | None = Field(default=None)

    is_linked: bool = Field(default=False)

    # Every canonical title this stands for. Nothing about a non-canonical row says which
    # of them a caller with room for one means, so nothing here puts one ahead of
    # another.
    tmdb_title_links: list[TitleTmdbTitle] = Relationship(
        back_populates="linked_title",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "TitleTmdbTitle.title_id"},
    )

    # The other end of the same table: every non-canonical row standing for this one,
    # which only a canonical title ever has. A row with both stands for something and is
    # stood for by something, which is the one shape the levels never take.
    linked_title_links: list[TitleTmdbTitle] = Relationship(
        back_populates="tmdb_title",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "TitleTmdbTitle.tmdb_title_id",
        },
    )

    # TODO: Validate
    @property
    def tmdb_titles(self) -> list[Title]:
        """Every canonical title this stands for, in the order they were linked."""
        return [link.tmdb_title for link in self.tmdb_title_links]

    # TODO: Validate
    @property
    def tmdb_title_ids(self) -> list[uuid.UUID]:
        return [link.tmdb_title_id for link in self.tmdb_title_links]

    # TODO: Validate
    @property
    def sole_tmdb_title(self) -> Title | None:
        tmdb_titles = self.tmdb_titles
        if len(tmdb_titles) != 1:
            return None
        return tmdb_titles[0]

    # TODO: Validate
    @property
    def sole_tmdb_title_id(self) -> uuid.UUID | None:
        """The id of the canonical title this stands for, where there is one."""
        tmdb_title = self.sole_tmdb_title
        return tmdb_title.id if tmdb_title else None

    # TODO: Validate
    @property
    def tmdb_ids(self) -> list[int]:
        return [get_tmdb_id(tmdb_title.key) for tmdb_title in self.tmdb_titles]

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB id of the canonical title this stands for, where there is one.

        Read out of the canonical row's key rather than stored beside it, so a
        non-canonical row and the row it stands for can never disagree about which TMDB
        record that is.
        """
        tmdb_title = self.sole_tmdb_title
        if tmdb_title is None:
            return None
        return get_tmdb_id(tmdb_title.key)

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

    genres: list[TitleGenre] = Relationship(
        back_populates="title",
        cascade_delete=True,
    )

    watch_providers: list[TitleWatchProvider] = Relationship(
        back_populates="title",
        cascade_delete=True,
    )

    spoken_languages: list[TitleSpokenLanguage] = Relationship(
        back_populates="title",
        cascade_delete=True,
    )

    # TODO: Validate
    @property
    def spoken_language_codes(self) -> list[str]:
        return [language.code for language in self.spoken_languages]

    # TODO: Validate
    def set_spoken_languages(self, names_by_code: Mapping[str, str]) -> None:
        wanted = {
            code.strip(): name.strip()
            for code, name in names_by_code.items()
            if code.strip()
        }
        stored = {language.code: language for language in self.spoken_languages}
        for code, name in wanted.items():
            language = stored.get(code)
            if language is None:
                self.spoken_languages.append(
                    TitleSpokenLanguage(title_id=self.id, code=code, name=name),
                )
            elif language.name != name:
                language.name = name
        for code, language in stored.items():
            if code not in wanted:
                self.spoken_languages.remove(language)

    # TODO: Validate
    @property
    def genre_names(self) -> list[str]:
        return [genre.name for genre in self.genres]

    # TODO: Validate
    def upsert_genres(self, names: Iterable[str]) -> None:
        wanted = list(dict.fromkeys(name.strip() for name in names if name.strip()))
        stored = {genre.name: genre for genre in self.genres}
        for name in wanted:
            if name not in stored:
                self.genres.append(TitleGenre(title_id=self.id, name=name))
        for name, genre in stored.items():
            if name not in wanted:
                self.genres.remove(genre)

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
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
            selectinload(cls.tmdb_title_links),  # type: ignore[arg-type]
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

        `tmdb_title_locked` is only ever set by a `User`, so it is always
        protected. The canonical titles themselves are rows of `TitleTmdbTitle`
        rather than a column of this one, so an upsert cannot write them away and
        what honours the lock is whatever would go on to link them.
        """
        protected_keys = set(protected_keys or ()) | {
            "tmdb_title_validated_at",
            "is_linked",
        }
        return super().upsert(parent, existing_record, protected_keys)

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Title`."""
        base_title = f"{type(self).__name__}:"
        if self.name:
            base_title += f" {self.name}"
        if self.key:
            base_title += f" ({self.key})"
        if self.id:
            base_title += f" ({self.id})"
        if self.source is None:
            return base_title
        return f"{self.source}\n{base_title}"


# TODO: Validate
class BaseTitleTmdbTitle(SQLModel):
    """Base model for one of the canonical titles a `Title` stands for."""

    title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    tmdb_title_id: uuid.UUID = Field(
        foreign_key="title.id",
        ondelete="CASCADE",
    )
    note: str | None = Field(default=None)
    manual_tmdb_link: bool = Field(default=False)
    """Whether a `User` settled this link themselves. An automatic process never
    deletes or rewrites a link that carries it."""


# TODO: Validate
class TitleTmdbTitle(BaseTitleTmdbTitle, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        # Each canonical title is linked to a non-canonical row at most once; the leading
        # column also serves lookups of a row's canonical titles and cascade deletion
        # with it.
        PrimaryKeyConstraint("title_id", "tmdb_title_id"),
        # Used to find every non-canonical row standing for a canonical title.
        Index("TitleTmdbTitle-tmdb_title_id-index", "tmdb_title_id"),
    )

    # Both ends are a `Title`, so which foreign key each relationship follows has
    # to be named; nothing about the columns says which of them is which.
    linked_title: Title = Relationship(
        back_populates="tmdb_title_links",
        sa_relationship_kwargs={"foreign_keys": "TitleTmdbTitle.title_id"},
    )
    tmdb_title: Title = Relationship(
        back_populates="linked_title_links",
        sa_relationship_kwargs={
            "foreign_keys": "TitleTmdbTitle.tmdb_title_id",
        },
    )


# TODO: Validate
class BaseTitleGenre(SQLModel):
    title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    name: str = Field(min_length=1)


# TODO: Validate
class TitleGenre(BaseTitleGenre, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("title_id", "name"),
        Index("TitleGenre-name-index", "name"),
    )

    title: Title = Relationship(back_populates="genres")


# TODO: Validate
class BaseTitleSpokenLanguage(SQLModel):
    title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)


# TODO: Validate
class TitleSpokenLanguage(BaseTitleSpokenLanguage, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("title_id", "code"),
        Index("TitleSpokenLanguage-code-index", "code"),
    )

    title: Title = Relationship(back_populates="spoken_languages")


# TODO: Validate
class BaseTitleWatchProvider(SQLModel):
    title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    watch_provider_id: uuid.UUID = Field(
        foreign_key="watchprovider.id",
        ondelete="CASCADE",
    )
    region: str = Field(min_length=2, max_length=2)
    offering_type: str = Field(min_length=1)


# TODO: Validate
class TitleWatchProvider(BaseTitleWatchProvider, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint(
            "title_id",
            "region",
            "watch_provider_id",
            "offering_type",
        ),
        Index(
            "TitleWatchProvider-region-watch_provider_id-index",
            "region",
            "watch_provider_id",
        ),
    )

    title: Title = Relationship(back_populates="watch_providers")
    watch_provider: WatchProvider = Relationship()


# TODO: Validate
class BaseUnmatchedTitle(SQLModel):
    provider_name: str = Field(min_length=1)
    plugin_key: str | None = Field(default=None)
    ignored_at: datetime | None = DateTimeField(default=None)


# TODO: Validate
class UnmatchedTitle(BaseUnmatchedTitle, TimestampIdAndHashMixin, table=True):
    """A service TMDB says carries a canonical title that nothing here does.

    TMDB names every service a title streams on, and an import that reads one of
    those names finds either a plugin already carrying the title, a plugin that
    carries the service but not this title, or no plugin at all. The last two are
    what is written here, so the titles waiting on a source URL are a table to be
    worked through rather than something to be noticed by hand.
    """

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint(
            "title_id",
            "provider_name",
            name="UnmatchedTitle-title_id-provider_name-unique",
        ),
        Index("UnmatchedTitle-title_id-index", "title_id"),
    )

    title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    title: Title = Relationship()
