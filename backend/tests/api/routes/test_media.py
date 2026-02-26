# TODO: Validate
import uuid
from datetime import timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.media.models import EpisodeWatch
from app.media.schemas import SingleEpisodeWatchOutput, WatchedEpisodesOutput
from app.models import Message
from app.utils import tz_datetime
from tests.utils.media import get_random_episode, get_random_episode_watch
from tests.utils.test_assertions import (
    assert_not_authenticated,
    assert_not_found,
)
from tests.utils.user import create_user_api
from tests.utils.utils import random_lower_string


class TestPostWatchedEpisode:
    def test_post_episode_watch_defaults(self, client: TestClient, db: Session) -> None:
        user = create_user_api(client)
        episode = get_random_episode(db)
        db.commit()

        response = client.post(
            f"{settings.API_V1_STR}/media/episode-watches",
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
        user = create_user_api(client)
        episode = get_random_episode(db)
        db.commit()

        watch_date = tz_datetime.now() - timedelta(days=1)

        response = client.post(
            f"{settings.API_V1_STR}/media/episode-watches",
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

    def test_post_episode_watch_episode_not_found(self, client: TestClient) -> None:
        user = create_user_api(client)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/media/episode-watches",
            detail="Episode not found",
            headers=user.headers,
            parameters={"episode_id": str(uuid.uuid4())},
        )

    def test_post_episode_watch_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        episode = get_random_episode(db)
        db.commit()

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/media/episode-watches",
            parameters={"episode_id": str(episode.id)},
        )


class TestPatchWatchedEpisode:
    def test_patch_episode_watch_success(self, client: TestClient, db: Session) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)

        watch_date = tz_datetime.now()
        response = client.patch(
            f"{settings.API_V1_STR}/media/episode-watches/{episode_watch.id}",
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
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)

        response = client.patch(
            f"{settings.API_V1_STR}/media/episode-watches/{episode_watch.id}",
            headers=user.headers,
            json={"verified": True},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = SingleEpisodeWatchOutput.model_validate(response.json())
        assert parsed_response.id == episode_watch.id
        assert parsed_response.verified is True
        assert parsed_response.watch_date == episode_watch.watch_date

    def test_patch_episode_watch_not_found(self, client: TestClient) -> None:
        user = create_user_api(client)

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/media/episode-watches/{uuid.uuid4()}",
            detail="Episode watch not found",
            headers=user.headers,
            parameters={"verified": True},
        )

    def test_patch_episode_watch_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_user_api(client)
        user_2 = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user_1.id)

        response = client.patch(
            f"{settings.API_V1_STR}/media/episode-watches/{episode_watch.id}",
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
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/media/episode-watches/{episode_watch.id}",
            parameters={"verified": True},
        )


class TestDeleteWatchedEpisode:
    def test_delete_episode_watch_success(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)
        # Can't get the id after the entry is deleted so the value needs to be grabbed
        # now.
        episode_watch_id = episode_watch.id

        response = client.delete(
            f"{settings.API_V1_STR}/media/episode-watches/{episode_watch_id}",
            headers=user.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = Message.model_validate(response.json())
        assert parsed_response.message == "Episode watch deleted"

        # This is required for deletion to apply to the session.
        db.expire_all()
        deleted_watch = db.get(EpisodeWatch, episode_watch_id)
        assert deleted_watch is None

    def test_delete_episode_watch_not_found(self, client: TestClient) -> None:
        user = create_user_api(client)

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/media/episode-watches/{uuid.uuid4()}",
            detail="Episode watch not found",
            headers=user.headers,
        )

    def test_delete_episode_watch_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_user_api(client)
        user_2 = create_user_api(client)

        episode_watch = get_random_episode_watch(db, user_1.id)

        response = client.delete(
            f"{settings.API_V1_STR}/media/episode-watches/{episode_watch.id}",
            headers=user_2.headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Not authorized"

        db.expire_all()
        deleted_watch = db.get(EpisodeWatch, episode_watch.id)
        assert deleted_watch

    def test_delete_episode_watch_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)

        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/media/episode-watches/{episode_watch.id}",
        )

        db.expire_all()
        deleted_watch = db.get(EpisodeWatch, episode_watch.id)
        assert deleted_watch


class TestGetWatchedEpisodes:
    def test_get_watched_episodes_empty(self, client: TestClient) -> None:
        user = create_user_api(client)

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
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
        user = create_user_api(client)

        episode_1 = get_random_episode(db)
        episode_2 = get_random_episode(db)

        get_random_episode_watch(db, user.id, episode_1)
        get_random_episode_watch(db, user.id, episode_2)

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
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
        user = create_user_api(client)

        # Create 5 episode watches
        for _ in range(5):
            get_random_episode_watch(db, user.id)

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"skip": 0, "limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1 + 1 + 1 + 1
        assert len(parsed_response.watches) == 1 + 1

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"skip": 2, "limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1 + 1 + 1 + 1
        assert len(parsed_response.watches) == 1 + 1

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"skip": 4, "limit": 2},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1 + 1 + 1 + 1 + 1
        assert len(parsed_response.watches) == 1

    def test_get_watched_episodes_search_by_episode(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.name = random_lower_string(32)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.name = random_lower_string(32)
        db.commit()

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"episode_search": episode_watch.episode.name[:16]},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1

    def test_get_watched_episodes_search_by_season(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.name = random_lower_string(32)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.name = random_lower_string(32)
        db.commit()

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"season_search": episode_watch.episode.season.name[:16]},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1

    def test_get_watched_episodes_search_by_show(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.show.name = random_lower_string(32)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.show.name = random_lower_string(32)
        db.commit()

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"show_search": episode_watch.episode.season.show.name[:16]},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1

    def test_get_watched_episodes_search_by_source(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.show.source.name = random_lower_string(32)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.show.source.name = random_lower_string(32)
        db.commit()

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={
                "source_search": episode_watch.episode.season.show.source.name[:16],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 1

    def test_get_watched_episodes_search_no_results(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_user_api(client)
        episode_watch = get_random_episode_watch(db, user.id)
        episode_watch.episode.season.show.name = random_lower_string(32)
        db.commit()

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
            headers=user.headers,
            params={"show_search": random_lower_string(16)},
        )

        assert response.status_code == status.HTTP_200_OK
        parsed_response = WatchedEpisodesOutput.model_validate(response.json())
        assert parsed_response.count == 0
        assert not parsed_response.watches

    def test_get_watched_episodes_user_isolation(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_user_api(client)
        user_2 = create_user_api(client)
        get_random_episode_watch(db, user_1.id)

        response = client.get(
            f"{settings.API_V1_STR}/media/episode-watches",
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
            url=f"{settings.API_V1_STR}/media/episode-watches",
        )
