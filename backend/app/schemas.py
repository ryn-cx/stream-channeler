"""Shared schemas."""

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, SQLModel

from app.channels.models import Channel
from app.episodes.models import Episode
from app.models import MediaMixin
from app.playlists.models import Playlist
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.models import Watch

MEDIA_MODELS = Episode | Season | Show | Source | Plugin | Channel | Watch | Playlist


class Message(BaseModel):
    """Generic message."""

    message: str


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
