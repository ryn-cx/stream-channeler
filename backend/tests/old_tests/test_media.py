# TODO: Validate
import uuid
from datetime import timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.models import Message
from app.utils import tz_datetime
from app.watches.models import EpisodeWatch
from app.watches.schemas import SingleEpisodeWatchOutput, WatchedEpisodesOutput
from tests.old_tests.utils.media import create_random_episode, create_random_watch
from tests.old_tests.utils.test_assertions import (
    assert_not_authenticated,
    assert_not_found,
)
from tests.old_tests.utils.user import create_random_user_alt


class TestPostWatchedEpisode:
    def test_post_episode_watch_defaults(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        episode = create_random_episode(db)
        db.commit()

        response = client.post(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
            json={"episode_id": str(episode.id)},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = SingleEpisodeWatchOutput.model_validate(response.json())
        assert parsed_response.episode.id == episode.id
        assert parsed_response.verified is False
        assert parsed_response.watch_date is not None

    def test_post_episode_watch_params(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = create_random_episode(db)
        db.commit()

        watch_date = tz_datetime.now() - timedelta(days=1)

        response = client.post(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
            json={
                "episode_id": str(episode.id),
                "watch_date": watch_date.isoformat(),
                "verified": True,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = SingleEpisodeWatchOutput.model_validate(response.json())
        assert parsed_response.episode.id == episode.id
        assert parsed_response.verified is True
        assert parsed_response.watch_date == watch_date

    def test_post_episode_watch_episode_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/watches",
            detail="Episode not found",
            headers=user.headers,
            parameters={"episode_id": str(uuid.uuid4())},
        )

    def test_post_episode_watch_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        episode = create_random_episode(db)
        db.commit()

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/watches",
            parameters={"episode_id": str(episode.id)},
        )


class TestPatchWatchedEpisode:
    def test_patch_episode_watch_success(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        episode_watch = create_random_watch(db, user.id)

        watch_date = tz_datetime.now()
        response = client.patch(
            f"{settings.API_V1_STR}/episodes/watches/{episode_watch.id}",
            headers=user.headers,
            json={"verified": True, "watch_date": watch_date.isoformat()},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = SingleEpisodeWatchOutput.model_validate(response.json())
        assert parsed_response.id == episode_watch.id
        assert parsed_response.verified is True
        assert parsed_response.watch_date == watch_date

    def test_patch_episode_as_verified(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode_watch = create_random_watch(db, user.id)

        response = client.patch(
            f"{settings.API_V1_STR}/episodes/watches/{episode_watch.id}",
            headers=user.headers,
            json={"verified": True},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = SingleEpisodeWatchOutput.model_validate(response.json())
        assert parsed_response.id == episode_watch.id
        assert parsed_response.verified is True
        assert parsed_response.watch_date == episode_watch.watch_date

    def test_patch_episode_watch_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/watches/{uuid.uuid4()}",
            detail="Episode watch not found",
            headers=user.headers,
            parameters={"verified": True},
        )

    def test_patch_episode_watch_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        episode_watch = create_random_watch(db, user_1.id)

        response = client.patch(
            f"{settings.API_V1_STR}/episodes/watches/{episode_watch.id}",
            headers=user_2.headers,
            json={"verified": True},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Not authorized"

    def test_patch_episode_watch_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode_watch = create_random_watch(db, user.id)

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/watches/{episode_watch.id}",
            parameters={"verified": True},
        )


class TestDeleteWatchedEpisode:
    def test_delete_episode_watch_success(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode_watch = create_random_watch(db, user.id)
        # Can't get the id after the entry is deleted so the value needs to be grabbed
        # now.
        episode_watch_id = episode_watch.id

        response = client.delete(
            f"{settings.API_V1_STR}/episodes/watches/{episode_watch_id}",
            headers=user.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = Message.model_validate(response.json())
        assert parsed_response.message == "Episode watch deleted"

        db.expire_all()
        deleted_watch = db.exec(
            select(EpisodeWatch).where(EpisodeWatch.id == episode_watch_id),
        ).first()
        assert deleted_watch is None

    def test_delete_episode_watch_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/episodes/watches/{uuid.uuid4()}",
            detail="Episode watch not found",
            headers=user.headers,
        )

    def test_delete_episode_watch_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)

        episode_watch = create_random_watch(db, user_1.id)

        response = client.delete(
            f"{settings.API_V1_STR}/episodes/watches/{episode_watch.id}",
            headers=user_2.headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Not authorized"

        db.expire_all()
        deleted_watch = db.exec(
            select(EpisodeWatch).where(EpisodeWatch.id == episode_watch.id),
        ).first()
        assert deleted_watch

    def test_delete_episode_watch_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode_watch = create_random_watch(db, user.id)

        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/episodes/watches/{episode_watch.id}",
        )

        db.expire_all()
        deleted_watch = db.exec(
            select(EpisodeWatch).where(EpisodeWatch.id == episode_watch.id),
        ).first()
        assert deleted_watch


class TestGetWatchedEpisodes:
    def test_get_watched_episodes_empty(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)

        response = client.get(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 0
        assert not parsed_response.watches
        assert not parsed_response.episodes
        assert not parsed_response.seasons
        assert not parsed_response.shows
        assert not parsed_response.sources
        assert not parsed_response.plugins

    def test_get_watched_episodes_with_data(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        episode_1 = create_random_episode(db)
        episode_2 = create_random_episode(db)

        create_random_watch(db, user.id, episode_1)
        create_random_watch(db, user.id, episode_2)

        response = client.get(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1
        assert len(parsed_response.watches) == 1 + 1
        assert len(parsed_response.episodes) == 1 + 1
        assert len(parsed_response.seasons) == 1 + 1
        assert len(parsed_response.shows) == 1 + 1
        assert len(parsed_response.sources) == 1 + 1
        assert len(parsed_response.plugins) == 1 + 1
        assert episode_1.id in parsed_response.episodes
        assert episode_2.id in parsed_response.episodes

    def test_get_watched_episodes_pagination(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        # Create 5 episode watches
        for _ in range(5):
            create_random_watch(db, user.id)

        response = client.get(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
            params={"skip": 0, "limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1 + 1 + 1 + 1
        assert len(parsed_response.watches) == 1 + 1

        response = client.get(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
            params={"skip": 2, "limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1 + 1 + 1 + 1
        assert len(parsed_response.watches) == 1 + 1

        response = client.get(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user.headers,
            params={"skip": 4, "limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1 + 1 + 1 + 1
        assert len(parsed_response.watches) == 1

    def test_get_watched_episodes_user_isolation(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        create_random_watch(db, user_1.id)

        response = client.get(
            f"{settings.API_V1_STR}/episodes/watches",
            headers=user_2.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 0
        assert len(data["watches"]) == 0

    def test_get_watched_episodes_not_authenticated(self, client: TestClient) -> None:
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/episodes/watches",
        )
