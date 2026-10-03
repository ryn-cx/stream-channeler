# TODO: Validate

import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.users.utils import (
    auth_headers,
    create_random_superuser,
    create_random_user,
)

# A path parameter that names nothing, which is all an admin route's permission
# check needs.
MISSING = uuid.UUID("00000000-0000-0000-0000-000000000000")


# TODO: Validate
def assert_admin_only(
    client: TestClient,
    session: Session,
    method: Method,
    path: str,
) -> None:
    """Assert the route turns away everyone but an admin."""
    assert_requires_authentication(client, method, path, body={})
    assert_forbidden(
        client,
        method,
        path,
        auth_headers(create_random_user(session)),
        body={},
    )
    assert_allowed(
        client,
        method,
        path,
        auth_headers(create_random_superuser(session)),
        body={},
    )
