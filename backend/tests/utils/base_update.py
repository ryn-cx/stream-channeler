# TODO: Validate
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.users.utils import create_random_user_alt
from tests.utils.base import (
    MODELS_WITH_PARENT,
    OUTPUT_MODELS,
    OUTPUT_MODELS_WITH_KEY,
    PATCH_MODELS,
    SUPPORTED_MODELS,
    BaseTests,
)
from tests.utils.route_assertions import (
    assert_conflict,
    assert_not_found,
    assert_success,
)
from tests.utils.utils import build_random_model, dump_random_model


class BaseUpdateTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def get_record_from_db(self, db: Session, record_id: uuid.UUID) -> T:
        return db.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).one()

    def assert_modified_at_updated(
        self,
        db: Session,
        record_id: uuid.UUID,
        modified_at_before: datetime,
    ) -> None:
        db_record = self.get_record_from_db(db, record_id)
        assert db_record.modified_at >= modified_at_before

    def assert_db_matches_expected(
        self,
        db: Session,
        record: SUPPORTED_MODELS | OUTPUT_MODELS,
        update_model: PATCH_MODELS,
    ) -> None:
        db_record = self.get_record_from_db(db, record.id)
        output_type = type(record)

        merged = record.model_dump() | update_model.model_dump(exclude_unset=True)
        expected_data = output_type.model_validate(merged).model_dump()
        record_data = output_type.model_validate(db_record).model_dump()

        # modified_at was already checked separately.
        record_data.pop("modified_at", None)
        expected_data.pop("modified_at", None)

        assert record_data == expected_data

    def assert_db_updated(
        self,
        db: Session,
        record: SUPPORTED_MODELS | OUTPUT_MODELS,
        update_model: PATCH_MODELS,
        modified_at_before: datetime,
        records_before: Sequence[T],
    ) -> None:
        self.assert_modified_at_updated(db, record.id, modified_at_before)
        self.assert_db_matches_expected(db, record, update_model)
        self.assert_only_record_changed(db, record.id, records_before)

    def assert_update_data(
        self,
        client: TestClient,
        db: Session,
        record: SUPPORTED_MODELS | OUTPUT_MODELS,
        headers: dict[str, str],
        update_model: PATCH_MODELS,
    ) -> OUTPUT_MODELS:
        modified_at_before = self.get_record_from_db(db, record.id).modified_at
        records_before = db.exec(select(self.database_model)).all()

        content = assert_success(
            client=client,
            method="patch",
            url=self.entry_url(record.id),
            output_model=self.output_model,
            headers=headers,
            parameters=update_model.model_dump(mode="json", exclude_unset=True),
        )

        self.assert_db_updated(
            db,
            record,
            update_model,
            modified_at_before,
            records_before,
        )

        return content

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("model_type", ["owner", "other_owner", "unowned"])
    def test_update_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        model_type: str,
        public: bool,
    ) -> None:
        authenticated = user_type != "anonymous"

        setup = self.create_test_data(
            client,
            db,
            relationship=model_type,
            authenticated=authenticated,
            public=public,
        )

        update_model = build_random_model(self.patch_model)
        parameters = update_model.model_dump(mode="json", exclude_unset=True)

        if self.assert_write_permission(
            db,
            client,
            authenticated=authenticated,
            model_type=model_type,
            method="patch",
            url=self.entry_url(setup.record.id),
            detail=f"Not authorized to access this {self.model_name}",
            headers=setup.headers,
            parameters=parameters,
        ):
            self.assert_update_data(
                client,
                db,
                setup.record,
                setup.headers,
                update_model,
            )

    @pytest.mark.parametrize("update_mode", ["full", "minimal"])
    @pytest.mark.parametrize("create_mode", ["full", "minimal"])
    def test_update_data(
        self,
        client: TestClient,
        db: Session,
        create_mode: Literal["full", "minimal"],
        update_mode: Literal["full", "minimal"],
    ) -> None:
        setup = self.create_test_data(
            client,
            db,
            "owner",
            authenticated=True,
            public=False,
        )

        initial_model = build_random_model(self.patch_model, create_mode)
        created = self.assert_update_data(
            client,
            db,
            setup.record,
            setup.headers,
            initial_model,
        )

        update_model = build_random_model(self.patch_model, update_mode)
        self.assert_update_data(client, db, created, setup.headers, update_model)

    def test_update_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        parameters = dump_random_model(self.patch_model)
        with self.assert_no_db_change(db):
            assert_not_found(
                client=client,
                method="patch",
                url=self.entry_url(str(uuid.uuid4())),
                detail=f"{self.model_name} not found",
                headers=user.headers,
                parameters=parameters,
            )

    def test_update_shared_key(self, client: TestClient, db: Session) -> None:
        """Ensure updating a record works when another user owns a record with the same key."""
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        setup = self.create_test_data(
            client,
            db,
            "owner",
            authenticated=True,
            public=False,
        )
        created = self.output_model.model_validate(setup.record)
        assert isinstance(created, OUTPUT_MODELS_WITH_KEY)

        other_user = create_random_user_alt(client, db)
        self.create_record_function(db, user_id=other_user.id, key=created.key)

        update_model = build_random_model(self.patch_model)
        self.assert_update_data(client, db, created, setup.headers, update_model)

    def test_update_duplicate_key(self, client: TestClient, db: Session) -> None:
        """Ensure updating a record's key to match a sibling's key fails."""
        if not hasattr(self.database_model, "key"):
            pytest.skip("Model has no key field")

        user = create_random_user_alt(client, db)
        record = self.create_record_function(db, user_id=user.id)
        if isinstance(record, MODELS_WITH_PARENT):
            sibling = self.create_record_function(db, record.parent())
        else:
            sibling = self.create_record_function(db, user_id=user.id)
        sibling_output = self.output_model.model_validate(sibling)
        assert isinstance(sibling_output, OUTPUT_MODELS_WITH_KEY)

        parameters = dump_random_model(self.patch_model, key=sibling_output.key)
        with self.assert_no_db_change(db):
            assert_conflict(
                client=client,
                method="patch",
                url=self.entry_url(record.id),
                detail=f"{self.model_name} with this key already exists",
                headers=user.headers,
                parameters=parameters,
            )

    def test_update_injected_id(self, client: TestClient, db: Session) -> None:
        """Ensure injecting an id in the PATCH body does not change the record's id."""
        user = create_random_user_alt(client, db)
        record = self.create_record_function(db, user_id=user.id)

        update_model = build_random_model(self.patch_model)
        parameters = update_model.model_dump(mode="json", exclude_unset=True)
        parameters["id"] = str(uuid.uuid4())

        content = assert_success(
            client=client,
            method="patch",
            url=self.entry_url(record.id),
            output_model=self.output_model,
            headers=user.headers,
            parameters=parameters,
        )
        assert content.id == record.id
        assert self.get_record_from_db(db, record.id).id == record.id
