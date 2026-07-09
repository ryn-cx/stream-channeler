"""Shared schemas."""

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, Json
from sqlmodel import Session, SQLModel

from app.channels.models import Channel
from app.constants import SERVER_SIDE_THRESHOLD_MAXIMUM
from app.episodes.models import Episode
from app.files.models import File
from app.models import MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.models import Watch

MEDIA_MODELS = Episode | Season | Show | Source | Plugin | Channel | Watch | File


class Message(BaseModel):
    """Generic message."""

    message: str


class SortOption(BaseModel):
    """Sort option for a list of records."""

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    desc: bool = False


class FilterOption(BaseModel):
    """Filter option for a list of records.

    A plain string performs a text or boolean match. A [minimum, maximum] list performs
    a range match on datetime and numeric columns; either bound may be blank.
    """

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    value: str | list[str]


class ReadOptions(BaseModel):
    """Options for reading a list of records."""

    sort_options: Json[list[SortOption]] = Field(default="[]")  # type: ignore[arg-type]
    filter_options: Json[list[FilterOption]] = Field(default="[]")  # type: ignore[arg-type]
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=SERVER_SIDE_THRESHOLD_MAXIMUM)


class BaseInput(SQLModel):
    """Base class for input schemas."""

    model_config = ConfigDict(extra="forbid")  # type: ignore[assignment]


class BaseCreateWithParentAndKey[
    ModelT: MediaMixin[Any, Any],
    ParentT: Plugin | Source | Show | Season | User,
](BaseInput):
    """Base create schemas for models with a parent and a key field."""

    key: str

    def create(self, session: Session, model: type[ModelT], parent: ParentT) -> ModelT:
        """Create and return the record if it is does not already exist."""
        if model.get(session, parent, self.key):
            raise HTTPException(
                status_code=409,
                detail=f"{model.__name__} with this key already exists",
            )
        child = model.model_validate(self, update={model.parent_id_field(): parent.id})
        session.add(child)
        session.commit()
        session.refresh(child)
        return child


class BaseUpdateWithKey[ModelT: MediaMixin[Any, Any]](BaseInput):
    """Base update schemas for models with a key field."""

    key: str | None

    def update(self, session: Session, existing_record: ModelT) -> ModelT:
        """Update the `existing_record` and return it.

        Validates the new `key` is unique among its siblings.
        """
        if (
            self.key is not None
            and self.key != existing_record.key
            and existing_record.get(
                session,
                existing_record.parent,
                self.key,
            )
        ):
            detail = f"{type(existing_record).__name__} with this key already exists"
            raise HTTPException(status_code=409, detail=(detail))

        existing_record.sqlmodel_update(self.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(existing_record)
        return existing_record


class BaseUpdateWithoutKey[ModelT: Channel | Watch](BaseInput):
    """Base update schemas for models without a key field."""

    def update(self, session: Session, existing_record: ModelT) -> ModelT:
        """Update the `existing_record` and return it."""
        existing_record.sqlmodel_update(self.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(existing_record)
        return existing_record
