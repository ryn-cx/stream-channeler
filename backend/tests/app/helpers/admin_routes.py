# TODO: Validate
"""The one permission test every admin route answers to.

Media - plugins, sources, shows, seasons, episodes, files - belongs to nobody and
is the same for everybody, so its routes have one rule between them: an admin may
use them and nobody else may. The record an id names does not matter to that
rule, which is why these pass an id that names nothing: a superuser reaching a
missing record is answered 404, and 404 is the route letting the request through.
"""

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
