# TODO: Validate
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field

from app.episodes.schemas import EpisodeOutput
from app.models import Visibility
from app.playlists.models import BasePlaylist, BasePlaylistEpisode
from app.plugins.schemas import PluginOutput
from app.schemas import BaseInput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic


class PlaylistCreate(BaseInput, BasePlaylist):
    """Schema for creating a `Playlist`."""

    episode_ids: list[uuid.UUID] = Field(default_factory=list)


class PlaylistUpdate(BaseInput):
    """Schema for updating a `Playlist`."""

    name: str | None = Field(default=None)
    visibility: Visibility | None = Field(default=None)
    # If provided, the playlist's episodes are atomically replaced (every
    # existing ``PlaylistEpisode`` row is deleted and a fresh set inserted in
    # the supplied order). Omit to leave the existing episodes untouched.
    episode_ids: list[uuid.UUID] | None = Field(default=None)


class PlaylistOutput(BasePlaylist):
    """Schema for returning a `Playlist`."""

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    modified_at: datetime


class PlaylistEpisodeOutput(BasePlaylistEpisode):
    episode_id: uuid.UUID


class PlaylistDetailOutput(PlaylistOutput):
    episodes: list[PlaylistEpisodeOutput]


class PlaylistEpisodeWithExtrasOutput(EpisodeOutput):
    position: int
    watch_date: datetime | None = Field(default=None)
    verified: bool | None = Field(default=None)
    episode_watch_id: uuid.UUID | None = Field(default=None)


class PlaylistEpisodesOutput(BaseModel):
    episodes: list[PlaylistEpisodeWithExtrasOutput]
    seasons: dict[uuid.UUID, SeasonOutput]
    shows: dict[uuid.UUID, ShowPublic]
    sources: dict[uuid.UUID, SourcePublic]
    plugins: dict[uuid.UUID, PluginOutput]
