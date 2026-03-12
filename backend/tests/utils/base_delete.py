# TODO: Validate
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.users.utils import create_random_user_alt
from tests.utils.base import SUPPORTED_MODELS, BaseTests
from tests.utils.route_assertions import (
    assert_delete,
    assert_not_found,
)


class BaseDeleteTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def assert_delete_success(
        self,
        client: TestClient,
        db: Session,
        record: SUPPORTED_MODELS,
        headers: dict[str, str],
    ) -> None:
        assert_delete(
            client=client,
            url=self.entry_url(record.id),
            message=f"{self.model_name} deleted successfully",
            headers=headers,
        )
        assert not db.exec(
            select(self.database_model).where(self.database_model.id == record.id),
        ).first()

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("is_owner", [True, False])
    def test_delete_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        is_owner: bool,
        public: bool,
    ) -> None:
        authenticated = user_type != "anonymous"

        setup = self.create_test_data(
            client,
            db,
            is_owner=is_owner,
            authenticated=authenticated,
            public=public,
        )

        if self.assert_write_permission(
            db,
            client,
            authenticated=authenticated,
            is_owner=is_owner,
            method="delete",
            url=self.entry_url(setup.record.id),
            detail=f"Not authorized to access this {self.model_name}",
            headers=setup.headers,
        ):
            self.assert_delete_success(client, db, setup.record, setup.headers)

    def test_delete_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        with self.assert_no_db_change(db):
            assert_not_found(
                client=client,
                method="delete",
                url=self.entry_url(str(uuid.uuid4())),
                detail=f"{self.model_name} not found",
                headers=user.headers,
            )
