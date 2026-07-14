"""Episode schemas."""

import uuid

from pydantic import BaseModel

from app.episodes.models import BaseEpisode, Episode
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.seasons.models import Season


class EpisodeCreate(BaseCreateWithParentAndKey[Episode, Season], BaseEpisode):
    """Schema for creating an `Episode`."""


class EpisodeUpdate(
    make_model_with_all_fields_optional(BaseEpisode),
    BaseUpdateWithKey[Episode],
):
    """Schema for updating an `Episode`."""


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
