# TODO: Validate
"""Shared schemas."""

from enum import StrEnum
from typing import Annotated, Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, Json, create_model
from pydantic.fields import FieldInfo
from sqlmodel import Session, SQLModel

from app.channel_orders.models import ChannelOrder
from app.channels.models import Channel
from app.comments.models import Comment
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

USER_OWNED_MODELS = (
    Episode
    | Season
    | Show
    | Source
    | Plugin
    | Channel
    | Watch
    | File
    | ChannelOrder
    | Comment
)


# TODO: This can be improved upstream, this one changes return to Any as a workaround.
# Based on https://github.com/pydantic/pydantic/issues/12329#issuecomment-3382159312
# TODO: Validate
def make_model_with_all_fields_optional(cls: type[BaseModel]) -> Any:  # noqa: ANN401
    """Return a new Pydantic model based on `cls`, but with all fields optional."""
    # Note 1: I believe there isn't any need to look for conflicts with computed fields.
    fields = {
        field_name: _get_field_tuple(field_info)
        for field_name, field_info in cls.model_fields.items()
    }

    return create_model(
        f"{cls.__name__}_AllFieldsOptional",
        __doc__=cls.__doc__,
        **fields,
    )


# Based on https://github.com/pydantic/pydantic/issues/12329#issuecomment-3382159312
# TODO: Validate
def _get_field_tuple(field_info: FieldInfo) -> Any:  # noqa: ANN401
    """Return a tuple as required by Pydantic's ``create_model()`` API."""
    annotation = field_info.annotation
    # Note 2: A bare `None` annotation is converted to `type(None)` so the assertion is fine, but
    # I'm wondering if we should provide a sentinel to better differentiate this..
    if annotation is None:
        msg = "At this point, the annotation must be set. This is either a bug in Pydantic or the application."
        raise ValueError(msg)

    # Note 3: `issubclass()` expects a type as a first argument, and raises if not, so checking for this is necessary.
    # For instance, this fails with `issubclass(int | str, BaseModel)` (used to not be the case in <2.12,
    # see https://github.com/pydantic/pydantic/issues/12349).
    # Note 4: You may want to recursively parse `annotation`, e.g. what if it's `list[Model]`, `Model | None`?
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):  # pyright: ignore[reportUnnecessaryIsInstance]
        annotation = make_model_with_all_fields_optional(annotation)

    if field_info.is_required():  # Note 5: use `is_required()` instead of manually checking `default`/`default_factory`
        return (Annotated[annotation | None, field_info], None)

    return Annotated[annotation, field_info]


# TODO: Validate
class Message(BaseModel):
    """Generic message."""

    message: str


# TODO: Validate
class SortOption(BaseModel):
    """Sort option for a list of records."""

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    desc: bool = False


# TODO: Validate
class FilterOption(BaseModel):
    """Filter option for a list of records.

    A plain string performs a text or boolean match. A [minimum, maximum] list performs
    a range match on datetime and numeric columns; either bound may be blank.
    """

    # This is aliased to `id` to match the internal TanStack Table API.
    column: str = Field(alias="id")
    value: str | list[str]


# TODO: Validate
class ReadOptions(BaseModel):
    """Options for reading a list of records."""

    sort_options: Json[list[SortOption]] = Field(default="[]")  # type: ignore[arg-type]
    filter_options: Json[list[FilterOption]] = Field(default="[]")  # type: ignore[arg-type]
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=SERVER_SIDE_THRESHOLD_MAXIMUM)


# TODO: Validate
class RecordScope(StrEnum):
    """Which records an admin list endpoint returns."""

    owned = "owned"
    favorites = "favorites"
    public = "public"
    all = "all"


# TODO: Validate
class ScopedReadOptions(ReadOptions):
    """Read options for the admin list endpoints, which serve every scope tab.

    `scope` is a field rather than a standalone query param because a standalone
    param alongside a `Query()`-annotated model suppresses FastAPI's flattening.
    """

    scope: RecordScope = RecordScope.all


# TODO: Validate
class BaseInput(SQLModel):
    """Base class for input schemas."""

    model_config = ConfigDict(extra="forbid")  # type: ignore[assignment]


# TODO: Validate
class BaseCreateWithParentAndKey[
    ModelT: MediaMixin[Any, Any],
    ParentT: Plugin | Source | Show | Season | User,
](BaseInput):
    """Base create schemas for models with a parent and a key field."""

    key: str

    # TODO: Validate
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


# TODO: Validate
class BaseUpdateWithKey[ModelT: MediaMixin[Any, Any]](BaseInput):
    """Base update schemas for models with a key field."""

    key: str | None

    # TODO: Validate
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


# TODO: Validate
class BaseUpdateWithoutKey[ModelT: Channel | Watch | ChannelOrder | Comment](BaseInput):
    """Base update schemas for models without a key field."""

    # TODO: Validate
    def update(self, session: Session, existing_record: ModelT) -> ModelT:
        """Update the `existing_record` and return it."""
        existing_record.sqlmodel_update(self.model_dump(exclude_unset=True))
        session.commit()
        session.refresh(existing_record)
        return existing_record
