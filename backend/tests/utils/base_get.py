# TODO: Validate
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from tests.utils.base import SUPPORTED_MODELS, BaseTests, CreatedTestData
from tests.utils.route_assertions import (
    assert_not_found,
    assert_success,
    assert_success_list,
)


class BaseGetTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def get_record_list_url(self, parent_id: uuid.UUID | str) -> str:
        """Get the URL for the parent endpoint."""
        return f"{settings.API_V1_STR}/{self.parent_endpoint_name}/{parent_id}/{self.endpoint_name}"

    def can_get_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        """Return if the user can get a specific record based on itspermissions."""
        return (user_is_authenticated and user_is_owner) or record_is_public

    def assert_api_get_list_success(
        self,
        client: TestClient,
        session: Session,
        parent_id: uuid.UUID,
        headers: dict[str, str],
    ) -> None:
        """Assert that the get list endpoint returns the expected data."""
        response = assert_success_list(
            client,
            "get",
            self.get_record_list_url(parent_id),
            self.output_model,
            headers,
        )

        parent_column = getattr(self.database_model, self.parent_key_name)
        siblings_select = select(self.database_model).where(parent_column == parent_id)
        database_records = session.exec(siblings_select).all()

        assert len(response) == len(database_records)
        response_by_id = {item.id: item for item in response}
        for record in database_records:
            expected_dump = self.output_model.model_validate(record).model_dump()
            # This works as a check to make sure the responses are not empty
            response_dump = response_by_id[record.id].model_dump()
            assert expected_dump.items() <= response_dump.items()

    def assert_api_get_success(
        self,
        client: TestClient,
        initial_test_data: CreatedTestData[T],
    ) -> None:
        """Assert that the get endpoint returns the expected data."""
        response = assert_success(
            client=client,
            method="get",
            url=self.generic_record_url(initial_test_data.record.id),
            output_model=self.output_model,
            headers=initial_test_data.headers,
        )
        # Make sure the response is not completely empty
        assert response.id
        database_record = self.output_model.model_validate(initial_test_data.record)
        # Make sure returned data matches the datbase record
        assert database_record.model_dump().items() <= response.model_dump().items()

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_get_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
        )

        if self.can_get_record(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        ):
            self.assert_api_get_success(session_scoped_client, initial_test_data)
        else:
            self.assert_cannot_access(
                session_scoped_session,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method="get",
                url=self.generic_record_url(initial_test_data.record.id),
                model_name=self.model_name,
                headers=initial_test_data.headers,
            )

    def test_get_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=True,
        )

        assert_not_found(
            client=session_scoped_client,
            method="get",
            url=self.generic_record_url(str(uuid.uuid4())),
            detail=f"{self.model_name} not found",
            headers=initial_test_data.headers,
        )

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_list_permissions(
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
        if self.can_get_record(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        ):
            self.assert_api_get_list_success(
                session_scoped_client,
                session_scoped_session,
                initial_test_data.record.parent.id,
                initial_test_data.headers,
            )
        else:
            self.assert_cannot_access(
                session_scoped_session,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method="get",
                url=self.get_record_list_url(initial_test_data.record.parent.id),
                model_name=self.parent_name,
                headers=initial_test_data.headers,
            )

    @pytest.mark.parametrize("record_count", [0, 1, 2])
    def test_list_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        record_count: int,
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

        # Delete all existing records under this parent to start clean.
        parent_column = getattr(self.database_model, self.parent_key_name)
        for record in session_scoped_session.exec(
            select(self.database_model).where(parent_column == parent.id),
        ).all():
            session_scoped_session.delete(record)
        session_scoped_session.flush()

        for _ in range(record_count):
            self.create_record_function(session_scoped_session, parent)

        self.assert_api_get_list_success(
            session_scoped_client,
            session_scoped_session,
            parent.id,
            initial_test_data.headers,
        )


class UserOwnedGetMixin[T: SUPPORTED_MODELS](BaseGetTests[T]):
    """Mixin for models where the parent is the authenticated user (channels, plugins)."""

    def get_record_list_url(self, parent_id: uuid.UUID | str) -> str:  # noqa: ARG002
        return f"{settings.API_V1_STR}/{self.endpoint_name}"

    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    # Always true because the user id is taken from the authenticated user so there is
    # no way to get the records without being the owner.
    @pytest.mark.parametrize("user_is_owner", [True])
    # Always false because there is no way to try to access another user's records.
    @pytest.mark.parametrize("record_is_public", [False])
    def test_list_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        super().test_list_permissions(
            session_scoped_client,
            session_scoped_session,
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        )
