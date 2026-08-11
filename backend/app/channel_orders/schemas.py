# TODO: Validate
import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.channel_orders.models import BaseChannelOrder, ChannelOrder
from app.channels.schemas import SortKeyInput
from app.schemas import (
    BaseInput,
    BaseUpdateWithoutKey,
    RecordScope,
    ScopedReadOptions,
    make_model_with_all_fields_optional,
)


# TODO: Validate
class ChannelOrderConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
    )

    sort_by: list[SortKeyInput] = []
    random_seed: int | None = None


# TODO: Validate
class ChannelOrderCreate(BaseInput, BaseChannelOrder):
    """Schema for creating a `ChannelOrder`."""


# TODO: Validate
class ChannelOrderUpdate(
    make_model_with_all_fields_optional(BaseChannelOrder),
    BaseUpdateWithoutKey[ChannelOrder],
):
    """Schema for updating a `ChannelOrder`."""


# TODO: Validate
class ChannelOrderOutput(BaseChannelOrder):
    """Schema for returning a `ChannelOrder`."""

    id: uuid.UUID
    user_id: uuid.UUID | None


# TODO: Validate
class ChannelOrderListOutput(BaseChannelOrder):
    """Schema for returning a `ChannelOrder` alongside its owner.

    `user_id` and `username` are redacted on anonymous records unless the viewer owns
    the record or is an admin. `score` is not a secret, so one row shape serves every
    scope and every viewer.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None
    score: int


# TODO: Validate
class ChannelOrdersPublic(BaseModel):
    """Schema for returning a page of `ChannelOrder`s."""

    data: list[ChannelOrderListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class ChannelOrderReadOptions(ScopedReadOptions):
    """Read options for the `ChannelOrder` list.

    Defaults to `owned` rather than `ScopedReadOptions`'s `all`, so an unscoped read
    returns the `User`'s own `ChannelOrder`s instead of demanding admin rights.
    """

    scope: RecordScope = RecordScope.owned


# TODO: Validate
class ChannelOrderAdminUpdate(
    make_model_with_all_fields_optional(BaseChannelOrder),
    BaseInput,
):
    """Schema for an admin updating any field on a `ChannelOrder`."""

    score: int | None = Field(default=None)


# TODO: Validate
class ChannelOrderCopyInput(BaseInput):
    """Schema for copying an existing `ChannelOrder` into the user's account."""

    name: str | None = None
