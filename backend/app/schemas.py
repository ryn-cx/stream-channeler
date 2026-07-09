from pydantic import BaseModel, Field, Json
from sqlmodel import SQLModel

from app.constants import MAX_PAGE_SIZE


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
