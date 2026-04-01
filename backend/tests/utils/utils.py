# TODO: Validate
# ruff: noqa: S311 - These are just random strings for testing and nothing needs to be
# cryptographically secure.
import random
import string
import uuid
from collections.abc import Callable
from datetime import date, datetime
from enum import Enum
from types import NoneType
from typing import Any, Literal, get_args, get_origin

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.config import settings
from app.utils import tz_datetime


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


def random_integer(min_value: int = 0, max_value: int = 2**16) -> int:
    """Get a random integer between min_value and max_value."""
    return random.randint(min_value, max_value)


def random_bool() -> bool:
    """Get a random boolean value."""
    return random.choice([True, False])


def random_past_timestamp(maximum_distance: int = 31536000) -> datetime:
    """Get a random timestamp in the past.

    Args:
        maximum_distance: Maximum time in seconds to subtract from the current time, by
        default one year.
    """
    current_timestamp = int(tz_datetime.now().timestamp())
    past_timestamp_minimum = current_timestamp - maximum_distance

    # Do not allow values less than 1 day because it can cause issues when converting to
    # a timezone-aware datetime.
    past_timestamp_minimum = max(past_timestamp_minimum, 86400)

    random_timestamp = random.randint(86400, current_timestamp)
    return tz_datetime.fromtimestamp(random_timestamp)


def random_future_timestamp(maximum_distance: int = 31536000) -> datetime:
    """Get a random timestamp in the future.

    Args:
        maximum_distance: Maximum time in seconds to add to the current time, by default
        one year.
    """
    current_timestamp = int(tz_datetime.now().timestamp())
    future_timestamp_max = current_timestamp + maximum_distance
    random_timestamp = random.randint(current_timestamp, future_timestamp_max)
    return tz_datetime.fromtimestamp(random_timestamp)


def random_optional_past_timestamp() -> datetime | None:
    """Get a random deleted_at timestamp.

    This function has a 50% chance of returning a random past timestamp or None.
    """
    if random_bool():
        return random_past_timestamp()
    return None


def random_optional_future_timestamp() -> datetime | None:
    """Get a random update_at timestamp.

    This function has a 50% chance of returning a random future timestamp or None.'
    """
    if random_bool():
        return random_future_timestamp()
    return None


_TYPE_GENERATORS: dict[type, Callable[[], object]] = {
    str: random_lower_string,
    int: random_integer,
    uuid.UUID: uuid.uuid4,
    datetime: random_past_timestamp,
    date: lambda: random_past_timestamp().date(),
    bool: random_bool,
}


def _is_nullable(annotation: type | None) -> tuple[bool, type]:
    """Return (is_nullable, inner_type) for a type annotation."""
    args = get_args(annotation)
    if args and NoneType in args:
        non_none = [a for a in args if a is not NoneType]
        if len(non_none) == 1:
            return True, non_none[0]
    assert annotation is not None
    return False, annotation


def _random_value(object_type: type) -> object:
    """Generate a random value for a given type."""
    generator = _TYPE_GENERATORS.get(object_type)
    if generator is not None:
        return generator()
    origin = get_origin(object_type)
    if origin is list:
        inner_args = get_args(object_type)
        inner_type = inner_args[0] if inner_args else str
        return [_random_value(inner_type) for _ in range(random.randint(1, 3))]
    if issubclass(object_type, Enum):
        return random.choice(list(object_type))
    if issubclass(object_type, BaseModel):
        return build_random_model(object_type)
    msg = f"No random generator for type: {object_type}"
    raise ValueError(msg)


def build_random_model[T: BaseModel](
    model: type[T],
    mode: Literal["random", "full", "minimal"] = "random",
    /,
    **required_kwargs: object,
) -> T:
    """Return a model instance with randomly populated fields.

    Args:
        _mode: "full" populates all fields including optionals, "minimal" only populates
            required fields, "random" (default) randomly includes optionals.
    """
    kwargs: dict[str, object] = dict(required_kwargs)
    for field_name, info in model.model_fields.items():
        if field_name in (*kwargs.keys(), "created_at", "modified_at"):
            continue
        if mode == "minimal" and not info.is_required():
            continue
        nullable, inner_type = _is_nullable(info.annotation)
        if mode != "full" and nullable:
            if random_bool():
                kwargs[field_name] = _random_value(inner_type)
        else:
            kwargs[field_name] = _random_value(inner_type)
    return model(**kwargs)  # type: ignore[return-value]


def dump_random_model(
    model: type[BaseModel],
    mode: Literal["random", "full", "minimal"] = "random",
    /,
    **required_kwargs: object,
) -> dict[str, Any]:
    """Return a JSON-serialized model with randomly populated fields."""
    return build_random_model(
        model,
        mode,
        **required_kwargs,
    ).model_dump(mode="json", exclude_unset=True)


def get_superuser_token_headers(client: TestClient) -> dict[str, str]:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}
