# TODO: Validate
import uuid
from datetime import datetime

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.constants import SERVER_SIDE_THRESHOLD_MAXIMUM
from app.schemas import make_model_with_all_fields_optional
from app.users.models import BaseUserSourcePreference, UserBase


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    username: str = Field(min_length=1, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(make_model_with_all_fields_optional(UserBase)):
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    username: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)
    server_side_threshold: int | None = Field(
        default=None,
        ge=0,
        le=SERVER_SIDE_THRESHOLD_MAXIMUM,
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


class SourcePreference(BaseUserSourcePreference):
    pass


class SourcePreferenceOutput(SourcePreference):
    name: str | None = None
    favicon_url: str | None = None
    episode_count: int
