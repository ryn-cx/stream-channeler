# TODO: Validate
"""Episode models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Never, Self, override

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

from app.canonical_media.filters import is_non_canonical
from app.canonical_media.keys import EPISODE_LEVEL, tmdb_id_of
from app.models import (
    BaseMediaMixin,
    DateTimeField,
    MediaMixin,
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


# The canonical row is the one a channel sorts on, so these name its columns and
# no copy's. A copy's own columns are only ever ordered by the admin tables, which
# order by any column they show and so are no reason to index these five.
CANONICAL_SORTABLE_FIELDS = [
    "air_date",
    "duration",
    "episode_number",
    "name",
    "sort_order",
]


# TODO: Validate
class BaseCanonicalEpisode(BaseMediaMixin):
    """The columns an episode carries, and so a copy of one carries too."""

    url: str | None = Field(default=None)
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    air_date: datetime | None = DateTimeField(default=None)
    episode_number: int | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    sort_order: int | None = Field(default=None)


# TODO: Validate
class BaseEpisode(BaseCanonicalEpisode):
    """Base model for an `Episode`."""

    canonical_episode_locked: bool = Field(default=False)
    canonical_episode_note: str | None = Field(default=None)


# TODO: Validate
class Episode(BaseEpisode, MediaMixin[Season, Never], table=True):
    """Model representing an episode, and a website's copy of one.

    A row is the episode itself when it points at no other, and one website's
    copy of an episode when it does. The episode itself hangs off the season
    itself the way a copy hangs off the season's copy, by the same `season_id`,
    so one primary key covers both.
    """

    PARENT_ID_FIELD: ClassVar[str] = "season_id"
    CANONICAL_ID_FIELD: ClassVar[str] = "canonical_episode_id"

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
        Index("Episode-canonical_episode_id-index", "canonical_episode_id"),
        # A copy names one episode at most, within the season holding it. The
        # show-wide rule this stands in for is still Python's to keep, since an
        # `Episode` has no `show_id` to constrain on. The episodes themselves are
        # no part of it: they are what the copies are counted against.
        Index(
            "Episode-live-season_id-canonical_episode_id-key",
            "season_id",
            "canonical_episode_id",
            unique=True,
            postgresql_where=text(
                "deleted_at IS NULL AND canonical_episode_id IS NOT NULL",
            ),
        ),
        # An episode is looked up by key alone where a `User` names a TMDB id
        # by hand, which is across every season rather than within one.
        Index(
            "Episode-canonical-key-index",
            "key",
            postgresql_where=text("canonical_episode_id IS NULL"),
        ),
        *sortable_field_indexes(
            "Episode",
            CANONICAL_SORTABLE_FIELDS,
            where=text("canonical_episode_id IS NULL"),
        ),
    )

    # The episode this is a copy of, and nothing when this is the episode itself.
    # Written by whatever imports the copy rather than filled in at the flush.
    canonical_episode_id: uuid.UUID = Field(
        default=None,
        nullable=True,
        foreign_key="episode.id",
    )
    # `remote_side` is what says which end of the join is the episode itself,
    # since both ends are the same table.
    canonical_episode: Episode | None = Relationship(
        sa_relationship=relationship(
            "Episode",
            remote_side="Episode.id",
            foreign_keys="Episode.canonical_episode_id",
        ),
    )

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB episode this is a copy of, if TMDB has a record of it."""
        if self.canonical_episode is None:
            return None
        return tmdb_id_of(self.canonical_episode.key, EPISODE_LEVEL)

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
    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Season)
            .join(Show, col(Season.show_id) == col(Show.id))
            .join(Source)
            .join(Plugin)
            .where(Season.id == self.season_id),
        ).one()

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return (
            select(cls)
            .where(is_non_canonical(cls))
            .join(Season, col(cls.season_id) == col(Season.id))
            .join(Show, col(Season.show_id) == col(Show.id))
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
                contains_eager(cls.season)  # type: ignore[arg-type]
                .contains_eager(Season.show)  # type: ignore[arg-type]
                .contains_eager(Show.source)  # type: ignore[arg-type]
                .contains_eager(Source.plugin)  # type: ignore[arg-type]
                .contains_eager(Plugin.user),  # type: ignore[arg-type]
            )
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

        `canonical_episode_locked` says who settled the link, and is
        always protected so that a later import never unsettles it. While it is
        set, the link an import works out never replaces the settled one.
        """
        protected_keys = set(protected_keys or ()) | {"canonical_episode_locked"}
        if existing_record and existing_record.canonical_episode_locked:
            protected_keys.add("canonical_episode_id")
        return super().upsert(parent, existing_record, protected_keys)

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Episode`."""
        return stringify_episode(self, self.season)


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
