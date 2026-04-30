# TODO: Validate
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field

from app.episodes.schemas import EpisodeOutput
from app.playlists.models import BasePlaylist, BasePlaylistEpisode
from app.plugins.schemas import PluginOutput
from app.schemas import BaseInput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic


class PlaylistOutput(BasePlaylist):
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


class PlaylistPostInput(BaseInput, BasePlaylist):
    # Order of ``episode_ids`` defines the saved order. The list is written in one
    # shot when the playlist is created; the episode list cannot be edited later.
    episode_ids: list[uuid.UUID] = Field(default_factory=list)


class PlaylistPatchInput(BaseInput):
    name: str | None = Field(default=None)
    public: bool | None = Field(default=None)
    # If provided, the playlist's episodes are atomically replaced (every
    # existing ``PlaylistEpisode`` row is deleted and a fresh set inserted in
    # the supplied order). Omit to leave the existing episodes untouched.
    episode_ids: list[uuid.UUID] | None = Field(default=None)
