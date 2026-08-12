# TODO: Validate
"""Canonical episode schemas."""

import uuid
from datetime import datetime
from typing import Self

from pydantic import AliasPath, BaseModel, ConfigDict, Field, model_validator

from app.canonical_episodes.models import BaseCanonicalEpisode
from app.canonical_media.keys import EPISODE_LEVEL, tmdb_id_of


# TODO: Validate
class CanonicalEpisodeOutput(BaseCanonicalEpisode):
    """Schema for returning a `CanonicalEpisode`."""

    canonical_season_id: uuid.UUID
    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        self.tmdb_id = tmdb_id_of(self.key, EPISODE_LEVEL)
        return self


# TODO: Validate
class CanonicalEpisodeListOutput(CanonicalEpisodeOutput):
    """Schema for returning a list of `CanonicalEpisode`s, with what holds them."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    canonical_season_name: str | None = Field(
        validation_alias=AliasPath("canonical_season", "name"),
    )
    canonical_show_id: uuid.UUID = Field(
        validation_alias=AliasPath("canonical_season", "canonical_show_id"),
    )
    canonical_show_name: str | None = Field(
        validation_alias=AliasPath("canonical_season", "canonical_show", "name"),
    )
    canonical_show_key: str | None = Field(
        validation_alias=AliasPath("canonical_season", "canonical_show", "key"),
    )


# TODO: Validate
class CanonicalEpisodesPublic(BaseModel):
    """Schema for returning a list of `CanonicalEpisode`s."""

    data: list[CanonicalEpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
