# TODO: Validate
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from tests.users.utils import authentication_token_from_email, create_random_user
from tests.utils.base import SUPPORTED_MODELS, BaseTests
from tests.utils.route_assertions import (
    assert_delete,
    assert_not_found,
)


class BaseDeleteTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def _can_delete_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        # ARG002 - Child implementations may need this value
        record_is_public: bool,  # noqa: ARG002
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def assert_delete_success(
        self,
        client: TestClient,
        session_scoped_db: Session,
        record: SUPPORTED_MODELS,
        headers: dict[str, str],
    ) -> None:
        assert_delete(
            client=client,
            url=self.generic_record_url(record.id),
            headers=headers,
            message=f"{self.model_name} deleted successfully",
        )
        assert not session_scoped_db.exec(
            select(self.database_model).where(self.database_model.id == record.id),
        ).first()

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_delete_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_db,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
        )

        if self._can_delete_record(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        ):
            self.assert_delete_success(
                session_scoped_client,
                session_scoped_db,
                initial_test_data.record,
                initial_test_data.headers,
            )
        else:
            self.assert_cannot_access(
                session_scoped_db,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method="delete",
                url=self.generic_record_url(initial_test_data.record.id),
                model_name=self.model_name,
                headers=initial_test_data.headers,
            )

    def test_delete_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_db: Session,
    ) -> None:
        user = create_random_user(session_scoped_db)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            db=session_scoped_db,
        )
        with self.assert_no_db_change(session_scoped_db):
            assert_not_found(
                client=session_scoped_client,
                method="delete",
                url=self.generic_record_url(str(uuid.uuid4())),
                detail=f"{self.model_name} not found",
                headers=user_headers,
            )
