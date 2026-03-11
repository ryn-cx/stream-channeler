# TODO: Validate
from __future__ import annotations

import uuid
from typing import Any, Literal, Protocol, runtime_checkable

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from tests.users.utils import create_random_user_alt
from tests.utils.base import (
    INPUT_SCHEMAS,
    MODELS_WITH_KEY,
    OUTPUT_MODELS,
    OUTPUT_MODELS_WITH_KEY,
    SUPPORTED_MODELS,
    BaseTests,
)
from tests.utils.route_assertions import (
    assert_conflict,
    assert_not_found,
    assert_success,
)
from tests.utils.utils import build_random_model, dump_random_model


@runtime_checkable
class HasID(Protocol):
    id: uuid.UUID


class BaseCreateTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def create_url(self, parent_id: uuid.UUID | str | None = None) -> str:
        """Return the URL used to create entries."""
        if parent_id:
            return f"{settings.API_V1_STR}/{self.parent_endpoint_name}/{parent_id}/{self.endpoint_name}"
        return f"{settings.API_V1_STR}/{self.endpoint_name}"

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID,
    ) -> tuple[uuid.UUID | None, Any]:
        """Create and return a parent record if possible."""
        if not self.has_parent:
            return None, None
        parent = self.create_parent_function(db, user_id=user_id)
        return parent.id, parent

    def create_records(
        self,
        db: Session,
        count: int,
        user_id: uuid.UUID,
        parent: Any,
    ) -> None:
        """Create and return records."""
        for _ in range(count):
            if parent is not None:
                self.create_record_function(db, parent)
            else:
                self.create_record_function(db, user_id=user_id)

    def get_shared_key_kwargs(
        self,
        client: TestClient,
        db: Session,
    ) -> dict[str, Any]:
        other_user = create_random_user_alt(client, db)
        existing = self.create_record_function(db, user_id=other_user.id)
        existing_output = self.output_model.model_validate(existing)
        assert isinstance(existing_output, OUTPUT_MODELS_WITH_KEY)
        return {"key": existing_output.key}

    def assert_create_success(
        self,
        client: TestClient,
        db: Session,
        parent_id: uuid.UUID | None,
        headers: dict[str, str],
        parameters_model: INPUT_SCHEMAS,
    ) -> None:
        parameters = parameters_model.model_dump(mode="json")

        records_before = db.exec(select(self.database_model)).all()

        content = assert_success(
            client=client,
            method="post",
            url=self.create_url(parent_id),
            output_model=self.output_model,
            headers=headers,
            parameters=parameters,
        )

        # Check the response from the API matches the input values.
        for key, value in parameters_model.model_dump().items():
            assert getattr(content, key) == value, (
                f"Expected {key!r} to be {value!r}, got {getattr(content, key)!r}"
            )

        # Check that the API response matches the database record.
        assert isinstance(content, HasID)
        self.assert_saved_to_db(db, content.id, content)

        # Check that existing records were not changed.
        self.assert_only_record_added(db, content.id, records_before)

    def assert_saved_to_db(
        self,
        db: Session,
        record_id: uuid.UUID,
        expected: OUTPUT_MODELS,
    ) -> None:
        record = db.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).one()
        assert type(expected).model_validate(record) == expected

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("model_type", ["owner", "other_owner", "unowned"])
    def test_create_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        model_type: str,
        public: bool,
    ) -> None:
        if not self.has_parent:
            pytest.skip("Model has no parent")

        authenticated = user_type != "anonymous"

        setup = self.create_test_data(
            client,
            db,
            relationship=model_type,
            authenticated=authenticated,
            public=public,
        )

        parent = getattr(setup.record, self.parent_key_name.removesuffix("_id"))
        parameters_model = build_random_model(self.input_schema)

        if self.assert_write_permission(
            db,
            client,
            authenticated=authenticated,
            model_type=model_type,
            method="post",
            url=self.create_url(parent.id),
            detail=f"Not authorized to access this {self.parent_name}",
            headers=setup.headers,
            parameters=parameters_model.model_dump(mode="json"),
        ):
            self.assert_create_success(
                client,
                db,
                parent.id,
                setup.headers,
                parameters_model,
            )

    @pytest.mark.parametrize("mode", ["full", "minimal"])
    def test_create_data(
        self,
        client: TestClient,
        db: Session,
        mode: Literal["full", "minimal"],
    ) -> None:
        if not self.has_parent:
            pytest.skip("Model has no parent")

        setup = self.create_test_data(
            client,
            db,
            relationship="owner",
            authenticated=True,
            public=False,
        )

        parent = getattr(setup.record, self.parent_key_name.removesuffix("_id"))
        parameters_model = build_random_model(self.input_schema, mode)

        self.assert_create_success(
            client,
            db,
            parent.id,
            setup.headers,
            parameters_model,
        )

    @pytest.mark.parametrize("existing_records", [1, 2])
    def test_create_with_existing_records(
        self,
        client: TestClient,
        db: Session,
        existing_records: int,
    ) -> None:
        if not self.has_parent:
            pytest.skip("Model has no parent")

        setup = self.create_test_data(
            client,
            db,
            relationship="owner",
            authenticated=True,
            public=False,
        )

        parent = getattr(setup.record, self.parent_key_name.removesuffix("_id"))
        self.create_records(db, existing_records, setup.user.id, parent)

        parameters_model = build_random_model(self.input_schema)

        self.assert_create_success(
            client,
            db,
            parent.id,
            setup.headers,
            parameters_model,
        )

    def test_create_shared_key(self, client: TestClient, db: Session) -> None:
        """Test creating a record when another user has a record with the same key."""
        if not self.has_parent or not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        setup = self.create_test_data(
            client,
            db,
            relationship="owner",
            authenticated=True,
            public=False,
        )

        parent = getattr(setup.record, self.parent_key_name.removesuffix("_id"))
        extra_kwargs = self.get_shared_key_kwargs(client, db)
        parameters_model = build_random_model(self.input_schema, **extra_kwargs)

        self.assert_create_success(
            client,
            db,
            parent.id,
            setup.headers,
            parameters_model,
        )

    def test_create_duplicate_key(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        if not self.has_parent or not hasattr(self.database_model, "key"):
            pytest.skip()

        user = create_random_user_alt(client, db)
        record = self.create_record_function(db, user_id=user.id)
        assert isinstance(record, MODELS_WITH_KEY)
        parent_id = getattr(record, self.parent_key_name)
        parameters = dump_random_model(self.input_schema, key=record.key)
        with self.assert_no_db_change(db):
            assert_conflict(
                client=client,
                method="post",
                url=self.create_url(parent_id),
                detail=f"{self.model_name} with this key already exists",
                headers=user.headers,
                parameters=parameters,
            )

    def test_create_parent_not_found(self, client: TestClient, db: Session) -> None:
        if not self.has_parent:
            pytest.skip("Model has no parent")

        user = create_random_user_alt(client, db)
        parameters = dump_random_model(self.input_schema)
        assert_not_found(
            client=client,
            method="post",
            url=self.create_url(str(uuid.uuid4())),
            detail=f"{self.parent_name} not found",
            headers=user.headers,
            parameters=parameters,
        )

    def test_create_generates_key(self, client: TestClient, db: Session) -> None:
        """Ensure a key is automatically generated when not provided."""
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        user = create_random_user_alt(client, db)
        parent_id, _ = self.create_parent(db, user.id)

        parameters = dump_random_model(self.input_schema, "minimal")

        content = assert_success(
            client=client,
            method="post",
            url=self.create_url(parent_id),
            output_model=self.output_model,
            headers=user.headers,
            parameters=parameters,
        )
        assert isinstance(content, HasID)
        assert isinstance(content, OUTPUT_MODELS_WITH_KEY)
        assert content.key
        self.assert_saved_to_db(db, content.id, content)

    def test_create_ignores_injected_id(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        """Verify that POST endpoint ignores a client-supplied id field."""
        user = create_random_user_alt(client, db)
        parent_id, _ = self.create_parent(db, user.id)

        parameters = dump_random_model(self.input_schema)
        parameters["id"] = str(uuid.uuid4())

        content = assert_success(
            client=client,
            method="post",
            url=self.create_url(parent_id),
            output_model=self.output_model,
            headers=user.headers,
            parameters=parameters,
        )

        assert content.id != parameters["id"]
