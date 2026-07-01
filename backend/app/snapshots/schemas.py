# TODO: Validate
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field

from app.episodes.schemas import EpisodeOutput
from app.models import Visibility
from app.plugins.schemas import PluginOutput
from app.schemas import BaseInput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.snapshots.models import BaseSnapshot, BaseSnapshotEpisode
from app.sources.schemas import SourcePublic


class SnapshotCreate(BaseInput, BaseSnapshot):
    """Schema for creating a `Snapshot`."""

    episode_ids: list[uuid.UUID] = Field(default_factory=list)


class SnapshotUpdate(BaseInput):
    """Schema for updating a `Snapshot`."""

    name: str | None = Field(default=None)
    visibility: Visibility | None = Field(default=None)
    anonymous: bool | None = Field(default=None)
    # If provided, the snapshot's episodes are atomically replaced (every
    # existing `SnapshotEpisode` row is deleted and a fresh set inserted in
    # the supplied order). Omit to leave the existing episodes untouched.
    episode_ids: list[uuid.UUID] | None = Field(default=None)


class SnapshotAdminUpdate(BaseInput, BaseSnapshot):
    """Schema for an admin updating any field on a `Snapshot`."""

    visibility: Visibility | None = Field(default=None)  # type: ignore[assignment]
    score: int | None = Field(default=None)


class SnapshotOutput(BaseSnapshot):
    """Schema for returning a `Snapshot`."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    score: int
    created_at: datetime
    modified_at: datetime


class SnapshotPublicOutput(BaseSnapshot):
    """Schema for returning a publicly listed `Snapshot`."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None


class SnapshotPublicListOutput(BaseModel):
    """Schema for returning a page of publicly listed `Snapshot`s."""

    data: list[SnapshotPublicOutput]
    count: int


class SnapshotAdminOutput(SnapshotOutput):
    """Schema for returning a `Snapshot` to an admin, including the owner username."""

    username: str | None


class SnapshotEpisodeOutput(BaseSnapshotEpisode):
    episode_id: uuid.UUID


class SnapshotDetailOutput(SnapshotOutput):
    episodes: list[SnapshotEpisodeOutput]


class SnapshotEpisodeWithExtrasOutput(EpisodeOutput):
    position: int
    watch_date: datetime | None = Field(default=None)
    verified: bool | None = Field(default=None)
    episode_watch_id: uuid.UUID | None = Field(default=None)


class SnapshotEpisodesOutput(BaseModel):
    episodes: list[SnapshotEpisodeWithExtrasOutput]
    seasons: dict[uuid.UUID, SeasonOutput]
    shows: dict[uuid.UUID, ShowPublic]
    sources: dict[uuid.UUID, SourcePublic]
    plugins: dict[uuid.UUID, PluginOutput]
