# TODO: Validate
# TODO: Compare this to the upstream implemenation
import sys
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
from tests.app.users.utils import (
    authentication_token_from_email,
)
from tests.app.utils.utils import get_superuser_token_headers

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
    """Drop everything in the test DB and recreate tables from current metadata."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    SQLModel.metadata.create_all(engine)


test_engine = create_test_engine("default")


# For every test session create a single database
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


def _init_connection() -> Generator[Connection]:
    """Create a connection and initialize the database."""
    connection = test_engine.connect()
    with Session(bind=connection) as session:
        init_db(session)
    yield connection
    connection.close()


@pytest.fixture
def function_scoped_connection() -> Generator[Connection]:
    yield from _init_connection()


@pytest.fixture(scope="class")
def class_scoped_connection() -> Generator[Connection]:
    yield from _init_connection()


@pytest.fixture(scope="module")
def module_scoped_connection() -> Generator[Connection]:
    yield from _init_connection()


@pytest.fixture(scope="session")
def session_scoped_connection() -> Generator[Connection]:
    yield from _init_connection()


@pytest.fixture
def function_scoped_session(
    function_scoped_connection: Connection,
) -> Generator[Session]:
    """Function-scoped database with per-test savepoint isolation."""
    yield from savepoint_session(function_scoped_connection)


@pytest.fixture
def class_scoped_session(class_scoped_connection: Connection) -> Generator[Session]:
    """Class-scoped database with per-test savepoint isolation."""
    yield from savepoint_session(class_scoped_connection)


@pytest.fixture
def module_scoped_session(module_scoped_connection: Connection) -> Generator[Session]:
    """Module-scoped database with per-test savepoint isolation."""
    yield from savepoint_session(module_scoped_connection)


@pytest.fixture
def session_scoped_session(session_scoped_connection: Connection) -> Generator[Session]:
    """Session-scoped database with per-test savepoint isolation."""
    yield from savepoint_session(session_scoped_connection)


def _create_client(session: Session) -> Generator[TestClient]:
    """Provide a test client that shares the given database session."""
    app.dependency_overrides[get_db] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def function_scoped_client(function_scoped_session: Session) -> Generator[TestClient]:
    """Provide a test client using a function-scoped database session."""
    yield from _create_client(function_scoped_session)


@pytest.fixture
def class_scoped_client(class_scoped_session: Session) -> Generator[TestClient]:
    """Provide a test client using a class-scoped database session."""
    yield from _create_client(class_scoped_session)


@pytest.fixture
def module_scoped_client(module_scoped_session: Session) -> Generator[TestClient]:
    """Provide a test client using a module-scoped database session."""
    yield from _create_client(module_scoped_session)


@pytest.fixture
def session_scoped_client(session_scoped_session: Session) -> Generator[TestClient]:
    """Provide a test client using a session-scoped database session."""
    yield from _create_client(session_scoped_session)


@pytest.fixture
def superuser_token_headers(session_scoped_client: TestClient) -> dict[str, str]:
    """Provide authentication headers for the superuser."""
    return get_superuser_token_headers(session_scoped_client)


@pytest.fixture
def normal_user_token_headers(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> dict[str, str]:
    """Provide authentication headers for a normal test user."""
    return authentication_token_from_email(
        client=session_scoped_client,
        email=settings.EMAIL_TEST_USER,
        session=session_scoped_session,
    )
