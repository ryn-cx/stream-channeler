"""Shared schemas."""

from datetime import datetime
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


class StringFilterOption(BaseModel):
    """String filter option for a list of records."""

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    value: str


class DateFilterOptionValue(BaseModel):
    """The value inside of DateFilterOption.value."""

    model_config = ConfigDict(populate_by_name=True)
    # This is aliased to `minimumDate` to simplify frontend code.
    minimum_date: datetime | None = Field(default=None, alias="minimumDate")
    # This is aliased to `maximumDate` to simplify frontend code.
    maximum_date: datetime | None = Field(default=None, alias="maximumDate")
    # This is aliased to `hideBlanks` to simplify frontend code.
    hide_blanks: bool = Field(default=False, alias="hideBlanks")


class DateFilterOption(BaseModel):
    """Date filter option for a list of records."""

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    # This is a seperate class to simplify frontend code.
    value: DateFilterOptionValue


class NumberFilterOptionValue(BaseModel):
    """The value inside of NumberFilterOption.value."""

    model_config = ConfigDict(populate_by_name=True)
    minimum: float | None = None
    maximum: float | None = None
    # This is aliased to `hideBlanks` to simplify frontend code.
    hide_blanks: bool = Field(default=False, alias="hideBlanks")


class NumberFilterOption(BaseModel):
    """Number range filter option for a list of records."""

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    # This is a seperate class to simplify frontend code.
    value: NumberFilterOptionValue


class ReadOptions(BaseModel):
    """Options for reading a list of records."""

    sort_options: Json[list[SortOption]] = Field(default="[]")  # type: ignore[arg-type]
    filter_options: Json[list[StringFilterOption]] = Field(default="[]")  # type: ignore[arg-type]
    date_filter_options: Json[list[DateFilterOption]] = Field(default="[]")  # type: ignore[arg-type]
    number_filter_options: Json[list[NumberFilterOption]] = Field(default="[]")  # type: ignore[arg-type]
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
