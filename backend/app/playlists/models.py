# TODO: Validate
import uuid

from sqlmodel import (
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


class BasePlaylist(SQLModel):
    name: str | None = Field(default=None)
    public: bool = Field(default=False)


class Playlist(BasePlaylist, TimestampIdAndHashMixin, table=True):
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

    def get_user_id(self, _session: Session) -> uuid.UUID:
        """Return the id of the user that owns this playlist."""
        return self.user_id

    def is_public(self, _session: Session) -> bool:
        """Return whether this playlist is publicly accessible."""
        return self.public


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
