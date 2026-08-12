# TODO: Validate
"""Canonical show schemas."""

import uuid
from datetime import datetime
from typing import Self

from pydantic import BaseModel, model_validator

from app.canonical_media.keys import SHOW_LEVEL, tmdb_id_of
from app.canonical_shows.models import BaseCanonicalShow
from app.media.canonical_metadata import tmdb_show_url


# TODO: Validate
class CanonicalShowOutput(BaseCanonicalShow):
    """Schema for returning a `CanonicalShow`.

    `tmdb_id` and `tmdb_url` are read back out of `key` rather than stored, since
    the key is the whole of what says which TMDB record a title is. They are
    served for reading only: nothing can be sorted or filtered by a value the
    database does not hold a column for.
    """

    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None
    tmdb_url: str | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        self.tmdb_id = tmdb_id_of(self.key, SHOW_LEVEL)
        self.tmdb_url = tmdb_show_url(self.key)
        return self


# TODO: Validate
class CanonicalShowsPublic(BaseModel):
    """Schema for returning a list of `CanonicalShow`s."""

    data: list[CanonicalShowOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
