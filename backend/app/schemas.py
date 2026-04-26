from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session, SQLModel

from app.channels.models import Channel
from app.episodes.models import Episode
from app.playlists.models import Playlist
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.watches.models import Watch


class Message(BaseModel):
    message: str


class BaseInput(SQLModel):
    """Base class for input schemas.

    Sets ``model_config = ConfigDict(extra="forbid")"``.
    """

    model_config = ConfigDict(extra="forbid")  # type: ignore[assignment]


MediaModel = Episode | Season | Show | Source | Plugin | Channel | Watch | Playlist


class BasePostInputWithChild[
    ModelT: Source | Show | Season | Episode,
    ParentT: Plugin | Source | Show | Season,
](BaseInput):
    """Generic base for post input schemas for models with a parent and a key field."""

    key: str

    def create(self, session: Session, model: type[ModelT], parent: ParentT) -> ModelT:
        """Check for existing, validate, add, commit, and return the new child."""
        # parent is a ParentT and model.get returns a ModelT or None.
        existing: ModelT | None = model.get(session, parent, self.key)  # type: ignore[arg-type, assignment]
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{type(existing).__name__} with this key already exists",
            )
        # model.model_validate returns a ModelT.
        child: ModelT = model.model_validate(  # type: ignore[assignment]
            self,
            update={model.parent_id_field(): parent.id},
        )
        session.add(child)
        session.commit()
        session.refresh(child)
        return child


class BasePatchInputWithKey[ModelT: Episode | Season | Show | Source | Plugin](
    BaseInput,
):
    """Generic base for patch input schemas for models with a key field."""

    key: str | None

    def update(self, session: Session, existing_record: ModelT) -> ModelT:
        """Apply the patch to ``existing_record`` and return it.

        Validates the new ``key`` is unique among siblings, then commits and
        refreshes.
        """
        if self.key is not None and self.key != existing_record.key:
            existing_with_key = existing_record.get(
                session,
                # existing_record.parent is a ParentT.
                existing_record.parent,  # type: ignore[arg-type]
                self.key,
            )
            if existing_with_key:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"{type(existing_with_key).__name__} with this "
                        "key already exists"
                    ),
                )
        existing_record.sqlmodel_update(self.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(existing_record)
        return existing_record


class BasePatchInputWithoutKey[ModelT: Channel | Plugin | Watch](BaseInput):
    """Generic base for patch input schemas for models without a key field."""

    def update(self, session: Session, existing_record: ModelT) -> ModelT:
        """Apply the patch to ``existing_record`` and return it."""
        existing_record.sqlmodel_update(self.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(existing_record)
        return existing_record
