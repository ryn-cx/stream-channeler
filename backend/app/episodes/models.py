# TODO: Validate
"""Episode models."""

import uuid
from collections.abc import Collection
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Never, Self, override

from sqlalchemy import text
from sqlalchemy.orm import contains_eager
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
    UniqueConstraint,
    col,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.keys import EPISODE_LEVEL, tmdb_id_of, watch_identifier
from app.models import (
    BaseMediaMixin,
    ChildMediaMixin,
    DateTimeField,
    TimestampIdAndHashMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

if TYPE_CHECKING:
    from app.issue_reports.models import EpisodeIssueReport
    from app.watches.models import Watch

# The prefix on a note that stands for a `User` having settled the link
# themselves, against the "Automatic: " an import writes. A lock says only that
# the link is settled, where what settled it is the difference between a
# decision worth keeping and a guess the import was sure enough of at the time,
# so the two are told apart by what was written down. What follows the prefix is
# free text, so a new way of recognising an episode needs nothing but its own
# wording, written where the matching is done.
MANUAL_NOTE_PREFIX = "Manual: "


# The canonical row is the one a channel sorts on, so these name its columns and no
# non-canonical row's. A non-canonical row's own columns are only ever ordered by the
# admin tables, which order by any column they show and so are no reason to index these
# five.
CANONICAL_SORTABLE_FIELDS = [
    "air_date",
    "duration",
    "episode_number",
    "name",
    "sort_order",
]


# TODO: Validate
class BaseCanonicalEpisode(BaseMediaMixin):
    """The columns an episode carries, and so a non-canonical row of one carries too."""

    url: str | None = Field(default=None)
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    thumbnail_url: str | None = Field(default=None)
    air_date: datetime | None = DateTimeField(default=None)
    episode_number: int | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    sort_order: int | None = Field(default=None)


# TODO: Validate
class BaseEpisode(BaseCanonicalEpisode):
    """Base model for an `Episode`."""

    canonical_episode_validated_at: datetime | None = DateTimeField(default=None)
    canonical_episode_note: str | None = Field(default=None)


# TODO: Validate
class Episode(BaseEpisode, ChildMediaMixin[Season, Never], table=True):
    PARENT_ID_FIELD: ClassVar[str] = "season_id"
    CANONICAL_FLAG_FIELD: ClassVar[str] = "is_canonical"

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
        CANONICAL_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        UniqueConstraint("id"),
        Index("Episode-deleted_at-index", "deleted_at"),
        Index("Episode-is_canonical-index", "is_canonical"),
        # An episode is looked up by key alone where a `User` names a TMDB id
        # by hand, which is across every season rather than within one.
        Index(
            "Episode-canonical-key-index",
            "key",
            postgresql_where=text("is_canonical IS TRUE"),
        ),
        # What every read of a `Watch` joins on. Across every row rather than
        # the episodes alone, since a watch carries the identifier of the link
        # that played it and is read back to the episode from there. Not unique:
        # the rows one watch counts for are all the rows carrying its
        # identifier, which is the whole of how one watch marks every listing of
        # the same media.
        Index(
            "Episode-watch_identifier-index",
            "watch_identifier",
        ),
        *sortable_field_indexes(
            "Episode",
            CANONICAL_SORTABLE_FIELDS,
            where=text("is_canonical IS TRUE"),
        ),
    )

    # Whether this row is the episode itself rather than one website's row standing for
    # it. Which episodes a non-canonical row stands for is stored in
    # `EpisodeCanonicalEpisode` and nowhere else, since a website that runs two episodes
    # together - a double-length first airing, a recap paired with the episode it recaps
    # - stands for each of them equally, and a column could only hold one.
    is_canonical: bool = Field(default=True)

    # Every episode this stands for. Nothing about a non-canonical row says which of
    # them a caller with room for one means, so nothing here puts one ahead of another.
    canonical_episode_links: list[EpisodeCanonicalEpisode] = Relationship(
        back_populates="episode",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "EpisodeCanonicalEpisode.episode_id",
        },
    )

    # The other end of the same table: every non-canonical row standing for this one,
    # which only a canonical episode ever has.
    non_canonical_episodes: list[EpisodeCanonicalEpisode] = Relationship(
        back_populates="canonical_episode",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "EpisodeCanonicalEpisode.canonical_episode_id",
        },
    )

    # TODO: Validate
    @property
    def canonical_episodes(self) -> list[Episode]:
        """Every episode this stands for, in the order they were linked."""
        return [link.canonical_episode for link in self.canonical_episode_links]

    # TODO: Validate
    @property
    def canonical_episode_ids(self) -> list[uuid.UUID]:
        """The id of every episode this stands for.

        Read off the links rather than off the episodes they point at, since the
        id is a column of the link itself and reading the episodes to ask them
        their own ids is a query per link for something already in hand.
        """
        return [link.canonical_episode_id for link in self.canonical_episode_links]

    # TODO: Validate
    @property
    def sole_canonical_episode(self) -> Episode | None:
        """The episode this stands for, where it stands for exactly one.

        A row that runs two episodes together stands for each of them as much as
        for any other, so there is no answer to give a caller with room for one
        and it is told there is none rather than handed whichever came first.
        """
        canonical_episodes = self.canonical_episodes
        if len(canonical_episodes) != 1:
            return None
        return canonical_episodes[0]

    # TODO: Validate
    @property
    def sole_canonical_episode_id(self) -> uuid.UUID | None:
        """The id of the episode this stands for, where there is one."""
        canonical_episode_ids = self.canonical_episode_ids
        if len(canonical_episode_ids) != 1:
            return None
        return canonical_episode_ids[0]

    # TODO: Validate
    def own_episode_numbers(self) -> Collection[int]:
        """Return the number this carries in the order its title is read in."""
        if self.episode_number is None:
            msg = f"Episode {self.id} has no episode number."
            raise ValueError(msg)
        return (self.episode_number,)

    # TODO: Validate
    @property
    def linked_sort_order(self) -> int | None:
        """Where this sits, as the link that was made for it says.

        A non-canonical row's place is the link's rather than the row's: the same row
        stands in a different place under each episode it was linked to, and only the
        link knows which of them is being read. A row with no link, and the episode
        itself, are ordered by the column they carry.
        """
        links = self.canonical_episode_links
        if len(links) != 1 or links[0].sort_order is None:
            return self.sort_order
        return links[0].sort_order

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB episode this is linked to, if TMDB has a record of it."""
        canonical_episode = self.sole_canonical_episode
        if canonical_episode is None:
            return None
        return tmdb_id_of(canonical_episode.key, EPISODE_LEVEL)

    # What a `Watch` is of. A plugin's own key names the media rather than one
    # row for it - a YouTube video is the same video under every playlist
    # carrying it - so the key paired with whoever issued it is what says two
    # rows are the same media.
    watch_identifier: str = Field(min_length=1)

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(back_populates="episodes")

    # Deleting an episode leaves its watches behind, detached, rather than
    # taking them with it. `passive_deletes` hands that to the database's
    # `ON DELETE SET NULL` instead of SQLAlchemy nulling each row itself.
    watches: list[Watch] = Relationship(
        back_populates="episode",
        sa_relationship_kwargs={"passive_deletes": True},
    )

    issue_reports: list[EpisodeIssueReport] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        # Listed whether the row is the record of the media or a non-canonical row of
        # one: a row is not hidden for being the record.
        return (
            select(cls)
            .join(Season, col(cls.season_id) == col(Season.id))
            .join(Show, col(Season.show_id) == col(Show.id))
            .join(Source)
            .join(Plugin)
        )

    # TODO: Validate
    @classmethod
    def select_with_plugin_eager(cls) -> SelectOfScalar[Self]:
        return cls.select_with_plugin().options(
            contains_eager(cls.season)  # type: ignore[arg-type]
            .contains_eager(Season.show)  # type: ignore[arg-type]
            .contains_eager(Show.source)  # type: ignore[arg-type]
            .contains_eager(Source.plugin),  # type: ignore[arg-type]
        )

    # TODO: Validate
    @property
    @override
    def parent(self) -> Season:
        return self.season

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Never]:
        return []

    # TODO: Validate
    @override
    def upsert(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        parent: Season,
        existing_record: Self | None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        """Upsert the `Episode`, keeping a locked the episode a `User` chose intact.

        `canonical_episode_locked` says who settled the links, and is always
        protected so that a later import never unsettles them. The links
        themselves are rows of their own and are no part of what an upsert
        writes, so nothing here has to hold them off.

        `is_canonical` is protected for the same reason a link is: a row that has been
        made a non-canonical row of something stays one, and an import writing the row
        again says nothing about that either way.

        `watch_identifier` is set here rather than by each plugin that builds an
        `Episode`, since the season being upserted onto is what says which plugin
        the row belongs to and every import arrives through this.
        """
        self.watch_identifier = watch_identifier(
            parent.show.source.plugin.key,
            self.key,
        )
        protected_keys = set(protected_keys or ()) | {
            "canonical_episode_validated_at",
            "is_canonical",
        }
        return super().upsert(parent, existing_record, protected_keys)

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Episode`."""
        return stringify_episode(self, self.season)


# TODO: Validate
class BaseEpisodeCanonicalEpisode(SQLModel):
    """Base model for one of the episodes an `Episode` stands for."""

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    canonical_episode_id: uuid.UUID = Field(
        foreign_key="episode.id",
        ondelete="CASCADE",
    )
    # Where the non-canonical row sits under the episode this link names. The
    # non-canonical row's own column says where the website filed the row, which is one
    # answer for a row that stands in a different place under each episode it was linked
    # to, so the place is the link's and the column is only what a row with no link
    # falls back on.
    sort_order: int | None = Field(default=None)


# TODO: Validate
class EpisodeCanonicalEpisode(
    BaseEpisodeCanonicalEpisode,
    TimestampIdAndHashMixin,
    table=True,
):
    """Model representing one of the episodes an `Episode` stands for.

    A website's row stands for one episode in the ordinary case and for several
    where the website ran them together, and there is nothing on the row that
    tells the two apart, so which ones it stands for is stored rather than
    inferred. This is the whole of that record: every episode a row stands for
    has a row here and none of them is held anywhere else, so a query asking
    which rows stand for an episode asks one table and no other.
    """

    __table_args__ = (
        # Each episode is linked to a non-canonical row at most once; the leading column
        # also serves lookups of a row's episodes and cascade deletion with it.
        PrimaryKeyConstraint("episode_id", "canonical_episode_id"),
        # Used to find every non-canonical row standing for an episode.
        Index(
            "EpisodeCanonicalEpisode-canonical_episode_id-index",
            "canonical_episode_id",
        ),
    )

    # Both ends are an `Episode`, so which foreign key each relationship follows
    # has to be named; nothing about the columns says which of them is which.
    episode: Episode = Relationship(
        back_populates="canonical_episode_links",
        sa_relationship_kwargs={
            "foreign_keys": "EpisodeCanonicalEpisode.episode_id",
        },
    )
    canonical_episode: Episode = Relationship(
        back_populates="non_canonical_episodes",
        sa_relationship_kwargs={
            "foreign_keys": "EpisodeCanonicalEpisode.canonical_episode_id",
        },
    )


# TODO: Validate
def stringify_episode(
    episode: Episode,
    parent: Season,
) -> str:
    """Return a string representation."""
    base_episode = f"{type(episode).__name__}:"
    if episode.episode_number:
        base_episode += f" {episode.episode_number} - "
    if episode.name:
        base_episode += f" {episode.name}"
    if episode.key:
        base_episode += f" ({episode.key})"
    if episode.id:
        base_episode += f" ({episode.id})"
    return f"{parent}\n{base_episode}"


# TODO: Validate
class BaseUserEpisodeUrl(SQLModel):
    url: str = Field(min_length=1)


# TODO: Validate
class UserEpisodeUrl(BaseUserEpisodeUrl, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "canonical_episode_id"),
        Index("UserEpisodeUrl-canonical_episode_id-index", "canonical_episode_id"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    canonical_episode_id: uuid.UUID = Field(
        foreign_key="episode.id",
        ondelete="CASCADE",
    )
    user: User = Relationship(back_populates="episode_urls")
