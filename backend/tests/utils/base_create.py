# TODO: Validate


import uuid
from typing import Literal, Protocol, runtime_checkable

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.users.models import User
from tests.users.utils import create_random_user
from tests.utils.base import (
    CREATE_SCHEMAS,
    OUTPUT_SCHEMAS,
    SUPPORTED_MODELS,
    BaseTests,
)
from tests.utils.route_assertions import (
    assert_conflict,
    assert_not_found,
    assert_success,
    assert_success_list,
    assert_unprocessable,
)
from tests.utils.utils import build_random_model, dump_random_model, random_bool


@runtime_checkable
class HasID(Protocol):
    id: uuid.UUID


class BaseCreateTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def create_record_url(self, parent_id: uuid.UUID | str | None = None) -> str:
        """Return the URL used to create a record."""
        if parent_id:
            return f"{settings.API_V1_STR}/{self.parent_endpoint_name}/{parent_id}/{self.endpoint_name}"
        return f"{settings.API_V1_STR}/{self.endpoint_name}"

    def create_parent(
        self,
        session_scoped_session: Session,
        user: User,
    ) -> SUPPORTED_MODELS | None | User:
        """Create and return a parent record if possible."""
        if not hasattr(self.database_model, "parent"):
            return None
        return self.create_parent_function(session_scoped_session, user)

    def can_create_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        # ARG002 - Child implementations may need this value
        record_is_public: bool,  # noqa: ARG002
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def assert_record_saved_to_db(
        self,
        session_scoped_session: Session,
        record_id: uuid.UUID,
        expected: OUTPUT_SCHEMAS,
    ) -> None:
        record = session_scoped_session.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).one()
        expected_dump = expected.model_dump()
        database_dump = type(expected).model_validate(record).model_dump()
        assert expected_dump.items() <= database_dump.items()

    def assert_create_record_success(
        self,
        client: TestClient,
        session_scoped_session: Session,
        parent_id: uuid.UUID | None,
        headers: dict[str, str],
        parameters_model: CREATE_SCHEMAS,
    ) -> OUTPUT_SCHEMAS:
        """Assert that a record was successfully created."""
        original_records = session_scoped_session.exec(
            select(self.database_model),
        ).all()

        # Watch return a list
        if self.returns_list:
            response = assert_success_list(
                client=client,
                method="post",
                url=self.create_record_url(parent_id),
                output_schema=self.output_schema,
                headers=headers,
                parameters=parameters_model.model_dump(mode="json", exclude_unset=True),
            )
            assert len(response) == 1
            result = response[0]
        else:
            result = assert_success(
                client=client,
                method="post",
                url=self.create_record_url(parent_id),
                output_schema=self.output_schema,
                headers=headers,
                parameters=parameters_model.model_dump(mode="json", exclude_unset=True),
            )

        # Check the response from the API matches the input values.
        input_dump = parameters_model.model_dump(exclude_unset=True)
        result_dump = result.model_dump()
        assert input_dump.items() <= result_dump.items()

        # Check that fields not provided in the input match their default values
        # (except id and foreign keys).
        extra_keys = (
            result_dump.keys()
            - input_dump.keys()
            - {"id"}
            - set(self.get_foreign_keys(self.database_model))
        )
        for key in extra_keys:
            info = self.output_schema.model_fields.get(key)
            if not info or info.is_required():
                # Required fields not in the input are server-generated (e.g. key).
                continue
            if info.default is not None:
                assert result_dump[key] == info.default, (
                    f"Expected {key!r} to be {info.default!r}, got {result_dump[key]!r}"
                )
            else:
                assert result_dump[key] is None, (
                    f"Expected {key!r} to be None, got {result_dump[key]!r}"
                )

        # Check that the API response matches the database record.
        self.assert_record_saved_to_db(session_scoped_session, result.id, result)

        # Check that only the new record was added.
        self.assert_only_records_added(
            session_scoped_session,
            [result.id],
            original_records,
        )

        return result

    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    @pytest.mark.parametrize("record_is_public", [True, False])
    def test_create_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
        )

        # Get parent before deleting the initial record.
        parent = initial_test_data.record.parent

        # Delete the initial record so this will only test creating for an empty parent,
        # this is done mostly to support watch better which has extra logic if there are
        # already existing records.
        session_scoped_session.delete(initial_test_data.record)

        if self.can_create_record(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        ):
            self.assert_create_record_success(
                session_scoped_client,
                session_scoped_session,
                parent.id,
                initial_test_data.headers,
                build_random_model(self.create_schema),
            )
        else:
            self.assert_cannot_access(
                session_scoped_session,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method="post",
                url=self.create_record_url(parent.id),
                model_name=self.parent_name,
                headers=initial_test_data.headers,
                parameters_model=build_random_model(self.create_schema),
            )

    @pytest.mark.parametrize("mode", ["full", "minimal"])
    def test_create_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        mode: Literal["full", "minimal"],
    ) -> None:
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        parent = initial_test_data.record.parent
        session_scoped_session.delete(initial_test_data.record)
        parameters_model = build_random_model(self.create_schema, mode)

        self.assert_create_record_success(
            session_scoped_client,
            session_scoped_session,
            parent.id,
            initial_test_data.headers,
            parameters_model,
        )

    @pytest.mark.parametrize("existing_record_count", [1, 2])
    def test_create_with_existing_records(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        existing_record_count: int,
    ) -> None:
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        parent = initial_test_data.record.parent
        for _ in range(existing_record_count - 1):
            self.create_record_function(session_scoped_session, parent)

        parameters_model = build_random_model(self.create_schema)

        self.assert_create_record_success(
            session_scoped_client,
            session_scoped_session,
            parent.id,
            initial_test_data.headers,
            parameters_model,
        )

    def test_create_shared_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Test creating a record when another user has a record with the same key."""
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=random_bool(),
        )

        parent = initial_test_data.record.parent
        other_user = create_random_user(session_scoped_session)
        existing_record = self.create_record_function(
            session_scoped_session,
            other_user.id,
        )
        parameters_model = build_random_model(
            self.create_schema,
            # union-attr - hasattr checks already ensure this attribute exists.
            key=existing_record.key,  # type: ignore[union-attr]
        )

        self.assert_create_record_success(
            session_scoped_client,
            session_scoped_session,
            parent.id,
            initial_test_data.headers,
            parameters_model,
        )

    def test_create_duplicate_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=random_bool(),
        )
        record = initial_test_data.record
        with self.assert_no_db_change(session_scoped_session):
            assert_conflict(
                client=session_scoped_client,
                method="post",
                url=self.create_record_url(getattr(record, self.parent_key_name)),
                detail=f"{self.model_name} with this key already exists",
                headers=initial_test_data.headers,
                # union-attr - hasattr checks already ensure this attribute exists.
                parameters=dump_random_model(self.create_schema, key=record.key),  # type: ignore[union-attr]
            )

    def test_create_parent_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=random_bool(),
        )

        with self.assert_no_db_change(session_scoped_session):
            assert_not_found(
                client=session_scoped_client,
                method="post",
                url=self.create_record_url(str(uuid.uuid4())),
                detail=f"{self.parent_name} not found",
                headers=initial_test_data.headers,
                parameters=dump_random_model(self.create_schema),
            )

    def test_create_generates_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Ensure a key is automatically generated when not provided."""
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=random_bool(),
        )
        result = self.assert_create_record_success(
            session_scoped_client,
            session_scoped_session,
            initial_test_data.record.parent.id,
            initial_test_data.headers,
            build_random_model(self.create_schema, "minimal"),
        )
        # union-attr - hasattr checks already ensure this attribute exists.
        assert result.key  # type: ignore[union-attr]


class UserOwnedCreateMixin[T: SUPPORTED_MODELS](BaseCreateTests[T]):
    """Mixin for models where the parent is the authenticated user (channels, plugins)."""

    def create_record_url(self, parent_id: uuid.UUID | str | None = None) -> str:  # noqa: ARG002
        return f"{settings.API_V1_STR}/{self.endpoint_name}"

    def create_parent(
        self,
        session_scoped_session: Session,  # noqa: ARG002
        user: User,
    ) -> User:
        return user

    # Creating a record without a user id is the same as creating while not
    # authenticated because the user id is taken directly from the authenticated user.
    @pytest.mark.skip
    def test_create_parent_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        pass

    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    # Always true because the user id is taken from the authenticated user so there is
    # no way to create the record and not be the owner.
    @pytest.mark.parametrize("user_is_owner", [True])
    @pytest.mark.parametrize("record_is_public", [True, False])
    def test_create_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        super().test_create_permissions(
            session_scoped_client,
            session_scoped_session,
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        )

    def test_create_rejects_extra_fields(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Verify that POST endpoint rejects extra fields."""
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        parent = self.create_parent(session_scoped_session, initial_test_data.user)

        parameters = dump_random_model(self.create_schema)
        parameters["id"] = str(uuid.uuid4())

        with self.assert_no_db_change(session_scoped_session):
            assert_unprocessable(
                session_scoped_client,
                "post",
                self.create_record_url(parent.id if parent else None),
                headers=initial_test_data.headers,
                parameters=parameters,
            )
