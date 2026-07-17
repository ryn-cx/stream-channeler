# TODO: Validate
import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.channel_orders.models import BaseChannelOrder, ChannelOrder
from app.channels.schemas import SortKeyInput
from app.schemas import (
    BaseInput,
    BaseUpdateWithoutKey,
    make_model_with_all_fields_optional,
)


class ChannelOrderConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )

    sort_by: list[SortKeyInput] = []
    random_seed: int | None = None


class ChannelOrderCreate(BaseInput, BaseChannelOrder):
    """Schema for creating a `ChannelOrder`."""


class ChannelOrderUpdate(
    make_model_with_all_fields_optional(BaseChannelOrder),
    BaseUpdateWithoutKey[ChannelOrder],
):
    """Schema for updating a `ChannelOrder`."""


class ChannelOrderOutput(BaseChannelOrder):
    """Schema for returning a `ChannelOrder`."""

    id: uuid.UUID
    user_id: uuid.UUID | None


class ChannelOrderPublicOutput(BaseChannelOrder):
    """Schema for returning a publicly listed `ChannelOrder`."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None


class ChannelOrderPublicListOutput(BaseModel):
    """Schema for returning a page of publicly listed `ChannelOrder`s."""

    data: list[ChannelOrderPublicOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


class ChannelOrderAdminOutput(ChannelOrderOutput):
    """Schema for returning a `ChannelOrder` to an admin, including score."""

    username: str | None
    score: int


class ChannelOrderAdminUpdate(
    make_model_with_all_fields_optional(BaseChannelOrder),
    BaseInput,
):
    """Schema for an admin updating any field on a `ChannelOrder`."""

    score: int | None = Field(default=None)


class ChannelOrderAdminListOutput(BaseModel):
    """Schema for returning a page of `ChannelOrder`s to an admin."""

    data: list[ChannelOrderAdminOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


class ChannelOrderCopyInput(BaseInput):
    """Schema for copying an existing `ChannelOrder` into the user's account."""

    name: str | None = None
