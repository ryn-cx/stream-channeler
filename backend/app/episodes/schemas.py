"""Episode schemas."""

import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.episodes.models import BaseEpisode, Episode
from app.schemas import BaseCreateWithParentAndKey, BaseUpdateWithKey
from app.seasons.models import Season


class EpisodeCreate(BaseCreateWithParentAndKey[Episode, Season], BaseEpisode):
    """Schema for creating an `Episode`."""


class EpisodeUpdate(BaseUpdateWithKey[Episode], BaseEpisode):
    """Schema for updating an `Episode`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment]


class EpisodeOutput(BaseEpisode):
    """Schema for returning an `Episode`."""

    id: uuid.UUID
    season_id: uuid.UUID


class EpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[EpisodeOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
