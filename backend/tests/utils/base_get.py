from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.users.utils import create_random_user_alt
from tests.utils.base import OUTPUT_MODELS, SUPPORTED_MODELS, BaseTests
from tests.utils.route_assertions import (
    assert_not_found,
    assert_success,
)


class BaseGetTests[T: SUPPORTED_MODELS](BaseTests[T]):
    def assert_get_success(
        self,
        client: TestClient,
        record: SUPPORTED_MODELS | OUTPUT_MODELS,
        headers: dict[str, str],
    ) -> None:
        content = assert_success(
            client=client,
            method="get",
            url=self.entry_url(record.id),
            output_model=self.output_model,
            headers=headers,
        )
        assert type(content).model_validate(record) == content

    # test_get_data is just combineed into this test because seperating it just
    # duplicates the thing that was tested here.
    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("model_type", ["owner", "other_owner", "unowned"])
    def test_get_permissions(
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

        if self.assert_read_permission(
            client,
            authenticated=authenticated,
            model_type=model_type,
            public=public,
            method="get",
            url=self.entry_url(setup.record.id),
            detail=f"Not authorized to access this {self.model_name}",
            headers=setup.headers,
        ):
            self.assert_get_success(client, setup.record, setup.headers)

    def test_get_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=self.entry_url(str(uuid.uuid4())),
            detail=f"{self.model_name} not found",
            headers=user.headers,
        )
