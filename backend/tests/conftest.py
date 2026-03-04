# TODO: Validate
from __future__ import annotations

import sys
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta
from functools import cache
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from loguru import logger
from pydantic_core import MultiHostUrl
from sqlalchemy import delete
from sqlmodel import Session, SQLModel, create_engine, text

# reportUnusedImport/F401 - This loads variables into the environment even if it looks
# like it does nothing. It's easier to do this on import than import it then have a
# function call in the middle of all of the imports.
import tests.old_tests.utils.load_test_env  # pyright: ignore[reportUnusedImport] # noqa: F401
from app.auth.dependencies import get_db
from app.config import settings
from app.database import init_db, load_models
from app.main import app
from app.plugins.models import Plugin
from app.plugins.plugins.utils.base_files import BaseFile
from tests.users.utils import (
    CreatedUser,
    authentication_token_from_email,
    create_random_user_alt,
)
from tests.utils.utils import get_superuser_token_headers, random_email

# Remove the uncolorized logger and replace it with a colorized one that captures debug
# logs.
logger.remove()
logger.add(sys.stdout, level="TRACE", colorize=True)


TEST_POSTGRES_DB = settings.POSTGRES_DB + "_test"

TEST_DATABASE_URI = MultiHostUrl.build(
    scheme="postgresql+psycopg",
    username=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
    host=settings.POSTGRES_SERVER,
    port=settings.POSTGRES_PORT,
    path=TEST_POSTGRES_DB,
)

test_engine = create_engine(str(TEST_DATABASE_URI))


@cache
def create_test_database() -> None:
    """Create the test database if it doesn't exist."""
    test_engine.dispose()
    # Use the default database settings to create the test database
    postgres_engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

    # Use raw connection with autocommit to avoid transaction block
    with postgres_engine.connect().execution_options(
        isolation_level="AUTOCOMMIT",
    ) as conn:
        # If the database already exists delete it
        conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_POSTGRES_DB}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{TEST_POSTGRES_DB}"'))

    # Create the tables in the test database
    load_models()
    SQLModel.metadata.create_all(test_engine)


def get_test_db() -> Generator[Session]:
    """Database dependency override for testing."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def db() -> Generator[Session]:
    """Provide a clean test database session for each test."""
    create_test_database()
    with Session(test_engine) as session:
        init_db(session)
        yield session

        session.execute(delete(Plugin))
        session.commit()


@pytest.fixture
def client() -> Generator[TestClient]:
    """Provide a test client with the test database dependency override."""
    # Override the get_db dependency so the test database is used
    app.dependency_overrides[get_db] = get_test_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def disable_ip_validation() -> Generator[None]:
    """Disable IP validation checks when downloading files for all tests."""
    with patch("app.plugins.plugins.YouTube.files.check_ip_matches"):
        with patch("app.plugins.plugins.YouTube.files.check_ip_not_matches"):
            yield


@pytest.fixture
def mock_download() -> Generator[None]:
    """Mock download_if_outdated and only update the timestamp.

    This will make it appear like the file was updated without having to actually
    download the file. The mock is automatically applied when this fixture is
    included as a test parameter.
    """

    def mock_download(self: BaseFile, update_at: datetime | None = None) -> None:
        # reportPrivateUsage - This is a private method being mocked for testing purposes.
        if self._is_outdated(update_at):  # pyright: ignore[reportPrivateUsage]
            # reportPrivateUsage - This is a private method being mocked for testing purposes.
            if getattr(self, "_database_entry_", None):  # pyright: ignore[reportPrivateUsage]
                # reportPrivateUsage - This is a private method being mocked for testing purposes.
                logger.debug(f"Mock Downloading {self._database_entry_.key}")  # pyright: ignore[reportPrivateUsage]
                if not update_at:
                    msg = "update_at should be provided in mock_download"
                    raise ValueError(msg)
                # reportPrivateUsage - This is a private method being mocked for testing purposes.
                self._database_entry_.data_timestamp = update_at + timedelta(  # pyright: ignore[reportPrivateUsage]
                    microseconds=1,
                )

    with patch.object(BaseFile, "download_if_outdated", mock_download):
        yield


# ARG001 - db parameter ensures the database is initialized before the client is created
@pytest.fixture
def superuser_token_headers(client: TestClient, db: Session) -> dict[str, str]:  # noqa: ARG001
    """Provide authentication headers for the superuser."""
    return get_superuser_token_headers(client)


@pytest.fixture
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    """Provide authentication headers for a normal test user."""
    return authentication_token_from_email(
        client=client,
        email=settings.EMAIL_TEST_USER,
        db=db,
    )


@pytest.fixture
def random_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    """Provide authentication headers for a randomly generated user."""
    return authentication_token_from_email(client=client, email=random_email(), db=db)


@pytest.fixture
def random_user(client: TestClient, db: Session) -> CreatedUser:
    """Create and return a randomly generated user with authentication headers."""
    return create_random_user_alt(client=client, db=db)


@pytest.fixture
def super_user(client: TestClient) -> CreatedUser:
    """Return the superuser credentials with authentication headers."""
    return CreatedUser(
        # This is a fake UUID for simplicity because it is not actually used.
        id=uuid.uuid4(),
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        headers=get_superuser_token_headers(client),
    )
