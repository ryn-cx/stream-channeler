# TODO: Validate
import uuid
from typing import override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
)

from app.episodes.models import Episode
from app.models import RootRecordMixin, TimestampIdAndHashMixin, Visibility
from app.users.models import User


class BasePlaylist(SQLModel):
    name: str | None = Field(default=None)
    visibility: Visibility = Field()


class Playlist(BasePlaylist, TimestampIdAndHashMixin, RootRecordMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Used to list all playlists owned by a user.
        Index("Playlist-user_id-index", "user_id"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="playlists")

    episodes: list[PlaylistEpisode] = Relationship(
        back_populates="playlist",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "PlaylistEpisode.position"},
    )

    @override
    def _root_record(self, session: Session) -> Playlist:
        return self


class BasePlaylistEpisode(SQLModel):
    # Position of the episode in the playlist (0-indexed).
    position: int = Field()


class PlaylistEpisode(BasePlaylistEpisode, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        # The same playlist cannot have two episodes at the same position.
        PrimaryKeyConstraint("playlist_id", "position"),
        # Used to cascade deletions when an episode is deleted.
        Index("PlaylistEpisode-episode_id-index", "episode_id"),
    )

    playlist_id: uuid.UUID = Field(foreign_key="playlist.id", ondelete="CASCADE")
    playlist: Playlist = Relationship(back_populates="episodes")

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    episode: Episode = Relationship()
