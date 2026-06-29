from pydantic import BaseModel, Field, Json
from sqlmodel import SQLModel

from app.constants import SERVER_SIDE_THRESHOLD


class Message(SQLModel):
    """Generic message."""

    message: str


class SortOption(BaseModel):
    column: str = Field(alias="id")
    desc: bool = False


class FilterOption(BaseModel):
    column: str = Field(alias="id")
    value: str


class ReadOptions(BaseModel):
    sort_options: Json[list[SortOption]] = Field(default="[]")  # type: ignore[arg-type]
    filter_options: Json[list[FilterOption]] = Field(default="[]")  # type: ignore[arg-type]
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=SERVER_SIDE_THRESHOLD, ge=1, le=SERVER_SIDE_THRESHOLD)
