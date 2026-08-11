# TODO: Validate
"""Issue report models."""

import uuid

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
)

from app.episodes.models import Episode
from app.models import TimestampIdAndHashMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User


# TODO: Validate
class BaseIssueReport(SQLModel):
    """Base model for an issue report."""

    report: str = Field(min_length=1)


# TODO: Validate
class IssueReportMixin(BaseIssueReport, TimestampIdAndHashMixin):
    """Mixin for the report tables hanging off each kind of media record.

    A report is about one website's copy of the media rather than the media
    itself, since what is wrong is normally what that site reported, so each kind
    of record has a table of its own rather than all three sharing one.

    Anyone reading the media can report what is wrong with it, so a report left
    by a visitor with no account has no `user_id` and nobody but a superuser can
    edit or delete it afterwards.
    """

    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="CASCADE",
    )


# TODO: Validate
class EpisodeIssueReport(IssueReportMixin, table=True):
    """Model representing what a `User` says is wrong with an `Episode`."""

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Used to list the reports left on one episode.
        Index("EpisodeIssueReport-episode_id-index", "episode_id"),
        # Used to list the reports written by a user.
        Index("EpisodeIssueReport-user_id-index", "user_id"),
    )

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    episode: Episode = Relationship(back_populates="issue_reports")

    user: User | None = Relationship()


# TODO: Validate
class SeasonIssueReport(IssueReportMixin, table=True):
    """Model representing what a `User` says is wrong with a `Season`."""

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Used to list the reports left on one season.
        Index("SeasonIssueReport-season_id-index", "season_id"),
        # Used to list the reports written by a user.
        Index("SeasonIssueReport-user_id-index", "user_id"),
    )

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(back_populates="issue_reports")

    user: User | None = Relationship()


# TODO: Validate
class ShowIssueReport(IssueReportMixin, table=True):
    """Model representing what a `User` says is wrong with a `Show`."""

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Used to list the reports left on one title.
        Index("ShowIssueReport-show_id-index", "show_id"),
        # Used to list the reports written by a user.
        Index("ShowIssueReport-user_id-index", "user_id"),
    )

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(back_populates="issue_reports")

    user: User | None = Relationship()
