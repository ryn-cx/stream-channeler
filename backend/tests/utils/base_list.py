# TODO: Validate
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from tests.utils.base import MODELS_WITH_PARENT, SUPPORTED_MODELS, BaseTests
from tests.utils.route_assertions import (
    assert_success,
)


class BaseListFromParentTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def parent_url(self, parent_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/{self.parent_endpoint_name}/{parent_id}/{self.endpoint_name}"

    def assert_list_success(
        self,
        client: TestClient,
        db: Session,
        parent_id: uuid.UUID,
        headers: dict[str, str],
    ) -> None:
        data = assert_success(
            client,
            "get",
            self.parent_url(parent_id),
            self.list_output_model,
            headers,
        )

        parent_column = getattr(self.database_model, self.parent_key_name)
        statement = select(self.database_model).where(parent_column == parent_id)
        db_records = db.exec(statement).all()
        expected = self.list_output_model.model_validate(
            {"data": db_records, "count": len(db_records)},
        )

        assert data == expected

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("is_owner", [True, False])
    def test_list_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        is_owner: bool,
        public: bool,
    ) -> None:
        if not issubclass(self.database_model, MODELS_WITH_PARENT):
            pytest.skip("Model has no parent")

        authenticated = user_type != "anonymous"

        setup = self.create_test_data(
            client,
            db,
            is_owner=is_owner,
            authenticated=authenticated,
            public=public,
        )
        parent = self.get_parent(db, setup.record)

        if self.assert_read_permission(
            client,
            authenticated=authenticated,
            is_owner=is_owner,
            public=public,
            method="get",
            url=self.parent_url(parent.id),
            detail=f"Not authorized to access this {self.parent_name}",
            headers=setup.headers,
        ):
            self.assert_list_success(client, db, parent.id, setup.headers)

    # 1 is skipped because it is tested by test_list_permissions
    @pytest.mark.parametrize("record_count", [0, 2])
    def test_list_data(
        self,
        client: TestClient,
        db: Session,
        record_count: int,
    ) -> None:
        if not issubclass(self.database_model, MODELS_WITH_PARENT):
            pytest.skip("Model has no parent")

        setup = self.create_test_data(
            client,
            db,
            is_owner=True,
            authenticated=True,
            public=False,
        )
        parent = self.get_parent(db, setup.record)

        if record_count == 0:
            db.delete(setup.record)
            db.flush()
        for _ in range(record_count - 1):
            self.create_record_function(db, parent)

        self.assert_list_success(client, db, parent.id, setup.headers)
