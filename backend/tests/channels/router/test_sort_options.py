from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.schemas import MultipleSortOptionOutputs
from app.config import settings
from tests.users.utils import create_random_user_alt
from tests.utils.route_assertions import assert_success

URL = f"{settings.API_V1_STR}/channels/sort-options"


# TODO: More detailed tests.
class TestSortOptions:
    def test_sort_options_anonymous(self, client: TestClient) -> None:
        result = assert_success(
            client=client,
            method="get",
            url=URL,
            output_model=MultipleSortOptionOutputs,
        )
        assert len(result.data) > 0

    def test_sort_options_authenticated(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        result = assert_success(
            client=client,
            method="get",
            url=URL,
            output_model=MultipleSortOptionOutputs,
            headers=user.headers,
        )
        assert len(result.data) > 0
