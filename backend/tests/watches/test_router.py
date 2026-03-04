import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.utils import tz_datetime
from app.watches.models import Watch
from app.watches.schemas import (
    WatchesListOutput,
    WatchOutput,
    WatchPatchInput,
    WatchPostInput,
)
from tests.episodes.utils import create_random_episode
from tests.old_tests.utils.test_assertions import assert_not_authenticated
from tests.users.utils import create_random_user, create_random_user_alt
from tests.utils.media_router import (
    BaseCreateTests,
    BaseDeleteTests,
    BaseGetTests,
    BaseTests,
    BaseUpdateTests,
)
from tests.utils.utils import dump_random_model
from tests.watches.utils import create_random_watch

WATCHES_URL = f"{settings.API_V1_STR}/watches"


class WatchTestMixin(BaseTests):
    has_parent = True
    database_model = Watch
    input_schema = WatchPostInput
    output_model = WatchOutput
    patch_model = WatchPatchInput
    endpoint_name = "watches"
    parent_endpoint_name = "episodes"
    parent_key_name = "episode_id"
    model_name = "Watch"
    parent_name = "Episode"

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> Episode:
        return create_random_episode(db, user_id=user_id)

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | Episode | User | Watch | None = None,
    ) -> Watch:
        if user_id is None:
            user_id = create_random_user(db).id
        if parent is not None:
            assert isinstance(parent, Episode)
            return create_random_watch(db, user_id=user_id, episode=parent)
        return create_random_watch(db, user_id=user_id)


class TestCreateWatch(WatchTestMixin, BaseCreateTests):
    def test_create_defaults(self, client: TestClient, db: Session) -> None:
        """Creating a watch with no parameters uses current time and verified=False."""
        user = create_random_user_alt(client, db)
        episode = self.create_parent(db, user_id=user.id)
        parameters = dump_random_model(WatchPostInput, mode="minimal")
        before = tz_datetime.now()

        response = client.post(
            self._create_url(episode.id),
            json=parameters,
            headers=user.headers,
        )

        after = tz_datetime.now()
        assert response.status_code == status.HTTP_200_OK
        data = WatchOutput.model_validate(response.json())
        assert data.verified is False
        watch_date = data.watch_date.astimezone(before.tzinfo)
        assert before <= watch_date <= after

    def test_create_explicit_values(self, client: TestClient, db: Session) -> None:
        """Explicit watch_date and verified=True are preserved, not overridden by defaults."""
        user = create_random_user_alt(client, db)
        episode = self.create_parent(db, user_id=user.id)
        parameters = dump_random_model(WatchPostInput, mode="full")

        response = client.post(
            self._create_url(episode.id),
            json=parameters,
            headers=user.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = WatchOutput.model_validate(response.json())
        assert data.verified == parameters["verified"]
        expected = tz_datetime.fromisotimestamp(parameters["watch_date"])
        assert data.watch_date == expected

    @pytest.mark.skip(reason="Watch has no key field")
    def test_create_duplicate_key(self, client: TestClient, db: Session) -> None:
        super().test_create_duplicate_key(client, db)

    @pytest.mark.skip(reason="There is no way to fake a user id")
    def test_create_wrong_user(self, client: TestClient, db: Session) -> None:
        super().test_create_wrong_user(client, db)

    @pytest.mark.skip(reason="Ownership does not apply to watches")
    def test_create_unowned(self, client: TestClient, db: Session) -> None:
        super().test_create_unowned(client, db)

    def test_create_not_authenticated(self, client: TestClient, db: Session) -> None:
        """Watch has no key field, so use count-based verification instead."""
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user.id)
        parameters = dump_random_model(self.input_schema)

        count_before = db.exec(
            select(func.count()).select_from(Watch),
        ).one()

        assert_not_authenticated(
            client=client,
            method="post",
            url=self._create_url(parent.id),
            parameters=parameters,
        )

        count_after = db.exec(
            select(func.count()).select_from(Watch),
        ).one()
        assert count_before == count_after


class TestGetWatch(WatchTestMixin, BaseGetTests):
    pass


class TestUpdateWatch(WatchTestMixin, BaseUpdateTests):
    pass


class TestDeleteWatch(WatchTestMixin, BaseDeleteTests):
    pass


class TestListWatches:
    def test_list(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        create_random_watch(db, user_id=user.id)

        response = client.get(WATCHES_URL, headers=user.headers)
        assert response.status_code == status.HTTP_200_OK
        output = WatchesListOutput.model_validate(response.json())
        assert output.count == 1

    def test_list_empty(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)

        response = client.get(WATCHES_URL, headers=user.headers)
        assert response.status_code == status.HTTP_200_OK
        output = WatchesListOutput.model_validate(response.json())
        assert output.count == 0

    def test_list_multiple(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        create_random_watch(db, user_id=user.id)
        create_random_watch(db, user_id=user.id)

        response = client.get(WATCHES_URL, headers=user.headers)
        assert response.status_code == status.HTTP_200_OK
        output = WatchesListOutput.model_validate(response.json())
        assert output.count == 2

    def test_list_only_own_watches(self, client: TestClient, db: Session) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        create_random_watch(db, user_id=user_1.id)
        create_random_watch(db, user_id=user_2.id)

        response = client.get(WATCHES_URL, headers=user_1.headers)
        assert response.status_code == status.HTTP_200_OK
        output = WatchesListOutput.model_validate(response.json())
        assert output.count == 1

    def test_list_not_authenticated(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        create_random_watch(db, user_id=user.id)

        assert_not_authenticated(client=client, method="get", url=WATCHES_URL)
