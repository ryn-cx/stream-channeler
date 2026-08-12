# TODO: Validate
import random
import string

from fastapi.testclient import TestClient

from app.config import settings


# TODO: Validate
def random_lower_string() -> str:
    # S311 - This does not need to be cryptographically secure.
    return "".join(random.choices(string.ascii_lowercase, k=32))  # noqa: S311


# TODO: Validate
def random_email() -> str:
    return f"{random_lower_string()}@{random_lower_string()}.com"


# TODO: Validate
def get_superuser_token_headers(client: TestClient) -> dict[str, str]:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    return {"Authorization": f"Bearer {a_token}"}
