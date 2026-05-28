# TODO: Validate


import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.schemas import SortOptionOutput
from app.config import settings
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.route_assertions import assert_success_list

SORT_OPTIONS_URL = f"{settings.API_V1_STR}/channels/sort-options"


class TestSortOptions:
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    def test_sort_options(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
    ) -> None:
        headers = {}
        if user_is_authenticated:
            user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=user.email,
                session=session_scoped_session,
            )
        result = assert_success_list(
            client=session_scoped_client,
            method="get",
            url=SORT_OPTIONS_URL,
            output_schema=SortOptionOutput,
            headers=headers,
        )
        assert len(result) > 0
