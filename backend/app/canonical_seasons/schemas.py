# TODO: Validate
"""Canonical season schemas."""

import uuid
from datetime import datetime
from typing import Self

from pydantic import AliasPath, BaseModel, ConfigDict, Field, model_validator

from app.canonical_media.keys import SEASON_LEVEL, tmdb_id_of
from app.canonical_seasons.models import BaseCanonicalSeason


# TODO: Validate
class CanonicalSeasonOutput(BaseCanonicalSeason):
    """Schema for returning a `CanonicalSeason`."""

    canonical_show_id: uuid.UUID
    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        self.tmdb_id = tmdb_id_of(self.key, SEASON_LEVEL)
        return self


# TODO: Validate
class CanonicalSeasonListOutput(CanonicalSeasonOutput):
    """Schema for returning a list of `CanonicalSeason`s, with the title above."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    canonical_show_name: str | None = Field(
        validation_alias=AliasPath("canonical_show", "name"),
    )
    canonical_show_key: str | None = Field(
        validation_alias=AliasPath("canonical_show", "key"),
    )


# TODO: Validate
class CanonicalSeasonsPublic(BaseModel):
    """Schema for returning a list of `CanonicalSeason`s."""

    data: list[CanonicalSeasonListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
