# ruff: noqa: S311 - These are just random strings for testing and nothing needs to be
# cryptographically secure.
import random
import string
from datetime import datetime

from fastapi.testclient import TestClient

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


def get_superuser_token_headers(client: TestClient) -> dict[str, str]:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}
