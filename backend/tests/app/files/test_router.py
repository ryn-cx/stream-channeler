# TODO: Validate
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from app.config import settings
from app.files.models import File
from app.files.schemas import (
    FileCreate,
    FileListPublic,
    FilePublic,
    FileUpdate,
)
from tests.app.files.utils import create_random_file
from tests.app.plugins.utils import create_random_plugin
from tests.app.utils.base import BaseTests, CreatedTestData
from tests.app.utils.base_create import BaseCreateTests
from tests.app.utils.base_delete import BaseDeleteTests
from tests.app.utils.base_get import BaseGetTests
from tests.app.utils.base_update import BaseUpdateTests
from tests.app.utils.route_assertions import Method, assert_not_found, make_request
from tests.app.utils.utils import build_random_model


# TODO: Validate
class FileTestMixin(BaseTests[File]):
    """Shared setup for the superuser-gated `File` endpoints.

    Every `File` endpoint sits behind `get_current_active_superuser`, so the
    "happy path" helper tests (which don't parametrize `user_is_superuser`)
    default the requester to a superuser, and the denial assertion only checks
    the status code because the 403 detail differs between the admin gate ("not
    enough privileges") and the ownership check ("Not authorized...").
    """

    database_model = File
    create_schema = FileCreate
    output_schema = FilePublic
    list_output_schema = FileListPublic
    update_schema = FileUpdate

    create_parent_function = staticmethod(create_random_plugin)
    create_record_function = staticmethod(create_random_file)

    # TODO: Validate
    @property
    def endpoint_name(self) -> str:
        # `File` endpoints live under the admin-only `/admin/files` router.
        return "admin/files"

    # TODO: Validate
    def get_record_list_url(self, parent_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/admin/plugins/{parent_id}/files"

    # TODO: Validate
    def create_record_url(self, parent_id: uuid.UUID | str | None = None) -> str:
        return f"{settings.API_V1_STR}/admin/plugins/{parent_id}/files"

    # TODO: Validate
    def create_test_data(  # noqa: PLR0913 - mirrors the base signature
        self,
        client: TestClient,
        session: Session,
        *,
        user_is_owner: bool,
        user_is_authenticated: bool,
        record_is_public: bool,
        user_is_superuser: bool = True,
    ) -> CreatedTestData[File]:
        return super().create_test_data(
            client,
            session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )

    # TODO: Validate
    def assert_cannot_access(  # noqa: PLR0913
        self,
        session: Session,
        client: TestClient,
        *,
        user_is_authenticated: bool,
        method: Method,
        url: str,
        model_name: str,  # noqa: ARG002 - kept to match the base signature
        headers: dict[str, str],
        parameters_model: SQLModel | None = None,
    ) -> None:
        # The 403 detail depends on whether the admin gate or the ownership
        # check rejected the request, so only the status code is asserted.
        parameters = (
            parameters_model.model_dump(mode="json") if parameters_model else None
        )
        expected_status = (
            status.HTTP_403_FORBIDDEN
            if user_is_authenticated
            else status.HTTP_401_UNAUTHORIZED
        )
        with self.assert_no_db_change(session):
            response = make_request(
                client,
                method,
                url,
                headers=headers,
                parameters=parameters,
            )
            assert response.status_code == expected_status


# TODO: Validate
class TestGetFile(FileTestMixin, BaseGetTests[File]):
    # TODO: Validate
    def can_get_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> bool:
        # The admin gate rejects every non-superuser (and the unauthenticated)
        # before the public/ownership check the base predicate performs.
        return (
            user_is_authenticated
            and user_is_superuser
            and super().can_get_record(
                user_is_authenticated=user_is_authenticated,
                user_is_owner=user_is_owner,
                record_is_public=record_is_public,
                user_is_superuser=user_is_superuser,
            )
        )

    # TODO: Validate
    def test_admin_list_requires_superuser(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """The global `/admin/files` list is superuser-only."""
        url = f"{settings.API_V1_STR}/admin/files"

        unauthenticated = make_request(session_scoped_client, "get", url, headers={})
        assert unauthenticated.status_code == status.HTTP_401_UNAUTHORIZED

        regular = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
            user_is_superuser=False,
        )
        forbidden = make_request(
            session_scoped_client,
            "get",
            url,
            headers=regular.headers,
        )
        assert forbidden.status_code == status.HTTP_403_FORBIDDEN

        admin = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
            user_is_superuser=True,
        )
        allowed = make_request(
            session_scoped_client,
            "get",
            url,
            headers=admin.headers,
        )
        assert allowed.status_code == status.HTTP_200_OK


# TODO: Validate
class TestCreateFile(FileTestMixin, BaseCreateTests[File]):
    # TODO: Validate
    def can_create_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> bool:
        # The admin gate rejects every non-superuser before the plugin's
        # editable check runs.
        return user_is_superuser and super().can_create_record(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )


# TODO: Validate
class TestUpdateFile(FileTestMixin, BaseUpdateTests[File]):
    # TODO: Validate
    @pytest.mark.parametrize("user_is_superuser", [True, False])
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_update_permissions(  # noqa: PLR0913 - parametrize axes
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> None:
        """Ensure only a superuser can update."""
        initial_test_data = self.create_test_data(
            client=session_scoped_client,
            session=session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )

        patch_input = build_random_model(self.update_schema)

        can_update = user_is_authenticated and user_is_superuser
        if can_update:
            self.assert_api_update_success(
                session_scoped_session,
                session_scoped_client,
                initial_test_data,
                patch_input,
            )
        else:
            self.assert_cannot_access(
                session_scoped_session,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method="patch",
                url=self.generic_record_url(initial_test_data.record.id),
                model_name=self.model_name,
                headers=initial_test_data.headers,
                parameters_model=patch_input,
            )


# TODO: Validate
class TestDeleteFile(FileTestMixin, BaseDeleteTests[File]):
    # TODO: Validate
    def _can_delete_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> bool:
        # The admin gate rejects every non-superuser before ownership is checked.
        return user_is_superuser and super()._can_delete_record(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )

    # TODO: Validate
    def test_delete_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        # Override the base test: a non-superuser is blocked by the admin gate
        # (403) before the missing-record lookup (404) can run, so a superuser
        # is required to exercise the 404 path.
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=True,
        )

        with self.assert_no_db_change(session_scoped_session):
            assert_not_found(
                client=session_scoped_client,
                method="delete",
                url=self.generic_record_url(str(uuid.uuid4())),
                detail=f"{self.model_name} not found",
                headers=initial_test_data.headers,
            )
