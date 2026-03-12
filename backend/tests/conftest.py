# TODO: Validate
from __future__ import annotations

import sys
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from loguru import logger
from pydantic_core import MultiHostUrl
from sqlalchemy import Connection, Engine
from sqlmodel import Session, SQLModel, create_engine, text

# reportUnusedImport/F401 - This loads variables into the environment even if it looks
# like it does nothing. It's easier to do this on import than import it then have a
# function call in the middle of all of the imports.
from app.auth.dependencies import get_db
from app.config import settings
from app.database import init_db, load_models
from app.main import app
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


def create_test_engine(db_suffix: str) -> Engine:
    """Create a test database with the given suffix and return its engine."""
    db_name = f"{settings.POSTGRES_DB}_test_{db_suffix}"

    postgres_engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    with postgres_engine.connect().execution_options(
        isolation_level="AUTOCOMMIT",
    ) as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
            {"db_name": db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    postgres_engine.dispose()

    uri = MultiHostUrl.build(
        scheme="postgresql+psycopg",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        path=db_name,
    )
    return create_engine(str(uri))


def reset_tables(engine: Engine) -> None:
    """Drop and recreate all tables on the given engine."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)


test_engine = create_test_engine("default")


# For every test sessuib create a single database
@pytest.fixture(scope="session", autouse=True)
def create_test_database() -> None:
    """Load models and create all tables in the default test database."""
    load_models()
    reset_tables(test_engine)


def savepoint_session(connection: Connection) -> Generator[Session]:
    """Create a savepoint session that rolls back after use."""
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()


@pytest.fixture
def db_connection() -> Generator[Connection]:
    connection = test_engine.connect()
    with Session(bind=connection) as session:
        init_db(session)
    yield connection
    connection.close()


@pytest.fixture
def not_db(db_connection: Connection) -> Generator[Session]:
    """Provide an isolated test database session that rolls back after each test."""
    yield from savepoint_session(db_connection)


@pytest.fixture(scope="session")
def db_class_connection() -> Generator[Connection]:
    connection = test_engine.connect()
    with Session(bind=connection) as session:
        init_db(session)
    yield connection
    connection.close()


@pytest.fixture
def db(db_class_connection: Connection) -> Generator[Session]:
    """Class-scoped database with per-test savepoint isolation."""
    yield from savepoint_session(db_class_connection)


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    """Provide a test client that shares the test database session."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# TODO: Can any of the below be removed?
@pytest.fixture
def superuser_token_headers(client: TestClient) -> dict[str, str]:
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
