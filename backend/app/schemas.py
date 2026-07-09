from typing import Annotated, Any

from pydantic import BaseModel, Field, Json, create_model
from pydantic.fields import FieldInfo
from sqlmodel import SQLModel

from app.constants import MAX_PAGE_SIZE


# Based on https://github.com/pydantic/pydantic/issues/12329#issuecomment-3382159312
def make_model_with_all_fields_optional(cls: type[BaseModel]) -> type[BaseModel]:
    """Returns a new Pydantic model based on `cls`, but with all fields optional."""
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
def _get_field_tuple(field_info: FieldInfo) -> Any:  # noqa: ANN401
    """Returns a tuple as required by Pydantic's ``create_model()`` API."""
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


class Message(SQLModel):
    """Generic message."""

    message: str


class SortOption(BaseModel):
    column: str = Field(alias="id")
    desc: bool = False


class FilterOption(BaseModel):
    column: str = Field(alias="id")
    value: str | list[str]


class ReadOptions(BaseModel):
    sort_options: Json[list[SortOption]] = Field(default="[]")  # type: ignore[arg-type]
    filter_options: Json[list[FilterOption]] = Field(default="[]")  # type: ignore[arg-type]
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)
