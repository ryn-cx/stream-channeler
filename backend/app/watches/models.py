# TODO: Validate
import uuid
from datetime import datetime

from sqlmodel import (
    DateTime,
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
)

from app.episodes.models import Episode
from app.models import TimestampIdAndHashMixin
from app.users.models import User
from app.utils import tz_datetime


# TODO: Validate
class BaseWatch(SQLModel):
    # call-overload - See TimestampAndIdMixin for an explanation.
    watch_date: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        default_factory=tz_datetime.now,
    )

    verified: bool = Field(default=False)


# TODO: Validate
class Watch(TimestampIdAndHashMixin, BaseWatch, table=True):
    __table_args__ = (
        # Keyed on the episode itself rather than on the non-canonical row, so a watch
        # keeps its identity after the non-canonical row it was recorded against is
        # deleted.
        PrimaryKeyConstraint("id"),
        # Used in episode_selector and watch services to look up a user's watches.
        Index("Watch-user_id-episode_id-index", "user_id", "episode_id"),
        # Used when an episode is deleted and its watches are detached.
        Index("Watch-episode_id-index", "episode_id"),
        # Used by watch_filters to match watches to canonical episodes.
        Index("Watch-watch_identifier-index", "watch_identifier"),
        # One watch per `User`, per episode, per moment.
        Index(
            "Watch-user_id-watch_identifier-watch_date-key",
            "user_id",
            "watch_identifier",
            "watch_date",
            unique=True,
        ),
        # Used in episode_selector._apply_hide_watched and
        # episode_selector._filter_show_counts to filter by verified watch status.
        Index("Watch-user_id-verified-index", "user_id", "verified"),
        # Used in episode_selector._build_last_watched to aggregate the latest watch
        # date per episode and in episode_selector._apply_recently_aired_sort.
        Index("Watch-watch_date-index", "watch_date"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="watched_episodes")

    # What the watch is of, as against the website's listing it was recorded
    # against in `episode_id`. A plugin's own key names the media rather than
    # one listing of it, so that key paired with whoever issued it is the whole
    # of what says which media this is - and pairing it is what keeps two
    # plugins that happen to issue the same key apart. Held as a bare string
    # rather than a foreign key so it goes on saying which media after every row
    # carrying it is gone.
    # The link that played this, named by who issued its key paired with the
    # key. What the watch counts for is worked out on the way back out: the
    # identifier is read to whatever row carries it and that row to the episode
    # it stands for, so a watch made on one website counts on every other. Kept
    # as a string rather than a foreign key so a watch outlives the link.
    watch_identifier: str

    # The episode the watch was recorded against, or None once that episode has
    # been deleted. Reads join through it, so a detached watch is dormant until
    # it is relinked.
    episode_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="episode.id",
        ondelete="SET NULL",
    )
    episode: Episode | None = Relationship(back_populates="watches")

    # TODO: Validate
    def owner_id(self, _session: Session) -> uuid.UUID:
        return self.user_id

    # TODO: Validate
    def is_publically_readable(self, _session: Session) -> bool:
        return False
