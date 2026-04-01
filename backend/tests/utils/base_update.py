from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.users.utils import create_random_user
from tests.utils.base import (
    OUTPUT_MODELS,
    PATCH_MODELS,
    SUPPORTED_MODELS,
    BaseTests,
    CreatedTestData,
)
from tests.utils.route_assertions import (
    assert_conflict,
    assert_not_found,
    assert_success,
    assert_success_list,
    assert_unprocessable,
)
from tests.utils.utils import build_random_model, dump_random_model


class BaseUpdateTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def assert_database_modified_at_updated(
        self,
        session_scoped_db: Session,
        record_id: uuid.UUID,
        original_modified_at: datetime,
    ) -> None:
        database_record = self.get_record_from_db(session_scoped_db, record_id)
        assert database_record.modified_at >= original_modified_at

    def assert_database_matches_expected(
        self,
        session_scoped_db: Session,
        original_record: T,
        patch_input: PATCH_MODELS,
    ) -> None:
        # Apply patch on top of the original record to get expected record.
        original_dump = self.output_model.model_validate(original_record).model_dump()
        patch_dump = patch_input.model_dump(exclude_unset=True)
        expected_dump = original_dump | patch_dump

        database_record = self.get_record_from_db(session_scoped_db, original_record.id)
        database_dump = self.output_model.model_validate(database_record).model_dump()

        # modified_at will not match and is checked independently.
        database_dump.pop("modified_at", None)
        expected_dump.pop("modified_at", None)

        assert database_dump == expected_dump

    def assert_database_updated(
        self,
        session_scoped_db: Session,
        patch_results: Sequence[OUTPUT_MODELS],
        patch_input: PATCH_MODELS,
        original_modified_at: datetime,
        original_records: Sequence[T],
    ) -> None:
        original_records_by_id = {record.id: record for record in original_records}
        for patch_result in patch_results:
            self.assert_database_modified_at_updated(
                session_scoped_db,
                patch_result.id,
                original_modified_at,
            )
            self.assert_database_matches_expected(
                session_scoped_db,
                original_records_by_id[patch_result.id],
                patch_input,
            )
        self.assert_other_records_unchanged(
            session_scoped_db,
            patch_results,
            original_records,
        )

    def assert_api_update_success(
        self,
        session_scoped_db: Session,
        client: TestClient,
        setup: CreatedTestData[T],
        patch_input: PATCH_MODELS,
    ) -> list[OUTPUT_MODELS]:
        record_id = setup.record.id
        original_record = self.get_record_from_db(session_scoped_db, record_id)
        original_records = session_scoped_db.exec(select(self.database_model)).all()

        # Watch return a list of records.
        if self.returns_list:
            results = assert_success_list(
                client=client,
                method="patch",
                url=self.generic_record_url(record_id),
                output_model=self.output_model,
                headers=setup.headers,
                parameters=patch_input.model_dump(mode="json", exclude_unset=True),
            )
            assert len(results) == 1
            result = results[0]
        else:
            result = assert_success(
                client=client,
                method="patch",
                url=self.generic_record_url(record_id),
                output_model=self.output_model,
                headers=setup.headers,
                parameters=patch_input.model_dump(mode="json", exclude_unset=True),
            )

        # Verify that the database matches the API input.
        self.assert_database_updated(
            session_scoped_db,
            [result],
            patch_input,
            original_record.modified_at,
            original_records,
        )

        # Verify that the database matches the API output.
        database_record = self.get_record_from_db(session_scoped_db, result.id)
        assert result.model_dump().items() <= database_record.model_dump().items()

        return [result]

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_update_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        """Ensure only the owner of a record can update it."""
        initial_test_data = self.create_test_data(
            client=session_scoped_client,
            db=session_scoped_db,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
        )

        patch_input = build_random_model(self.patch_model)

        if user_is_authenticated and user_is_owner:
            self.assert_api_update_success(
                session_scoped_db,
                session_scoped_client,
                initial_test_data,
                patch_input,
            )
        else:
            self.assert_cannot_access(
                session_scoped_db,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method="patch",
                url=self.generic_record_url(initial_test_data.record.id),
                model_name=self.model_name,
                headers=initial_test_data.headers,
                parameters_model=patch_input,
            )

    @pytest.mark.parametrize("update_mode", ["full", "minimal"])
    @pytest.mark.parametrize("create_mode", ["full", "minimal"])
    def test_update_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
        create_mode: Literal["full", "minimal"],
        update_mode: Literal["full", "minimal"],
    ) -> None:
        """Ensure updating a record works correctly."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_db,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        # Manually update the existing record to match the expected initial state.
        initial_model = build_random_model(self.patch_model, create_mode)
        initial_test_data.record.sqlmodel_update(
            initial_model.model_dump(exclude_unset=True),
        )
        session_scoped_db.flush()

        update_model = build_random_model(self.patch_model, update_mode)
        self.assert_api_update_success(
            session_scoped_db,
            session_scoped_client,
            initial_test_data,
            update_model,
        )

    def test_update_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
    ) -> None:
        """Ensure updating a non-existent record returns a 404 error."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_db,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=True,
        )

        parameters = dump_random_model(self.patch_model)
        with self.assert_no_db_change(session_scoped_db):
            assert_not_found(
                client=session_scoped_client,
                method="patch",
                url=self.generic_record_url(str(uuid.uuid4())),
                detail=f"{self.model_name} not found",
                headers=initial_test_data.headers,
                parameters=parameters,
            )

    def test_update_shared_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
    ) -> None:
        """Ensure updating a record works when keys overlap between users."""
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_db,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        # union-attr - hasattr checks already ensure this attribute exists.
        key = initial_test_data.record.key  # type: ignore[union-attr]
        other_user = create_random_user(session_scoped_db)
        self.create_record_function(session_scoped_db, other_user.id, key=key)

        update_model = build_random_model(self.patch_model)
        self.assert_api_update_success(
            session_scoped_db,
            session_scoped_client,
            initial_test_data,
            update_model,
        )

    def test_update_duplicate_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
    ) -> None:
        """Ensure updating a record's key to match a sibling's key fails."""
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")
        if not hasattr(self.database_model, "parent"):
            pytest.skip("Model has no parent field")

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_db,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        record = initial_test_data.record
        sibling = self.create_record_function(session_scoped_db, record.parent())

        # union-attr - hasattr checks already ensure this attribute exists.
        parameters = dump_random_model(self.patch_model, key=sibling.key)  # type: ignore[union-attr]
        with self.assert_no_db_change(session_scoped_db):
            assert_conflict(
                client=session_scoped_client,
                method="patch",
                url=self.generic_record_url(record.id),
                detail=f"{self.model_name} with this key already exists",
                headers=initial_test_data.headers,
                parameters=parameters,
            )

    def test_update_resists_injecting_id(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
    ) -> None:
        """Ensure injecting an id does not change the record's id."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_db,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        update_model = build_random_model(self.patch_model)
        parameters = update_model.model_dump(mode="json", exclude_unset=True)
        parameters["id"] = str(uuid.uuid4())

        with self.assert_no_db_change(session_scoped_db):
            assert_unprocessable(
                session_scoped_client,
                "patch",
                self.generic_record_url(initial_test_data.record.id),
                headers=initial_test_data.headers,
                parameters=parameters,
            )
