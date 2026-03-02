import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.media.models import Episode
from app.media.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
)
from tests.utils.media import (
    get_random_episode,
    get_random_season,
)
from tests.utils.test_assertions import (
    assert_conflict,
    assert_delete,
    assert_not_authenticated,
    assert_not_found,
    assert_saved_to_db,
    assert_success,
)
from tests.utils.user import create_random_user_alt
from tests.utils.utils import dump_random_model


class TestCreateEpisode:
    def test_create_episode(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user.id)
        data = dump_random_model(EpisodePostInput, season_id=season.id)

        content = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/",
            output_model=EpisodeOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(db, Episode, content.id, data)

    def test_create_episode_season_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/",
            detail="Season not found",
            headers=user.headers,
            parameters=dump_random_model(EpisodePostInput, season_id=uuid.uuid4()),
        )

    def test_create_episode_duplicate_key(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user.id)
        original_episode = episode.model_dump(mode="json")

        assert_conflict(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/",
            detail="Episode with this key already exists",
            headers=user.headers,
            parameters=dump_random_model(
                EpisodePostInput,
                season_id=episode.season_id,
                key=episode.key,
            ),
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)

    def test_create_episode_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user_1.id)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/",
            detail="Season not found",
            headers=user_2.headers,
            parameters=dump_random_model(EpisodePostInput, season_id=season.id),
        )
        episodes = db.exec(select(Episode).where(Episode.season_id == season.id)).all()
        assert len(episodes) == 0

    def test_create_episode_unowned_season(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/",
            detail="Season not found",
            headers=user.headers,
            parameters=dump_random_model(EpisodePostInput, season_id=season.id),
        )
        episodes = db.exec(select(Episode).where(Episode.season_id == season.id)).all()
        assert len(episodes) == 0

    def test_create_episode_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user.id)

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/episodes/",
            parameters=dump_random_model(EpisodePostInput, season_id=season.id),
        )
        episodes = db.exec(select(Episode).where(Episode.season_id == season.id)).all()
        assert len(episodes) == 0


class TestListEpisodesFromSeason:
    def test_list_episodes_from_season(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user.id)

        response = client.get(
            f"{settings.API_V1_STR}/seasons/{episode.season_id}/episodes",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = EpisodesListOutput.model_validate(response.json())
        assert content.count == 1

    def test_list_episodes_from_season_empty(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user.id)

        response = client.get(
            f"{settings.API_V1_STR}/seasons/{season.id}/episodes",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = EpisodesListOutput.model_validate(response.json())
        assert content.count == 0

    def test_list_episodes_from_season_multiple(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user.id)
        get_random_episode(db, season=season)
        get_random_episode(db, season=season)

        response = client.get(
            f"{settings.API_V1_STR}/seasons/{season.id}/episodes",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = EpisodesListOutput.model_validate(response.json())
        assert content.count == 2

    def test_list_episodes_from_season_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/seasons/{uuid.uuid4()}/episodes",
            detail="Season not found",
            headers=user.headers,
        )

    def test_list_episodes_from_season_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user_1.id)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/seasons/{season.id}/episodes",
            detail="Season not found",
            headers=user_2.headers,
        )

    def test_list_episodes_from_season_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/seasons/{season.id}/episodes",
            detail="Season not found",
            headers=user.headers,
        )

    def test_list_episodes_from_season_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = get_random_season(db, user_id=user.id)
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/seasons/{season.id}/episodes",
        )


class TestUpdateEpisode:
    def test_update_episode(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user.id)
        data = dump_random_model(EpisodePatchInput)

        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            output_model=EpisodeOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(
            db,
            Episode,
            episode.id,
            episode.model_dump(mode="json") | data,
            updated=True,
        )

    def test_update_episode_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_uuid = uuid.uuid4()

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/{random_uuid}",
            detail="Episode not found",
            headers=user.headers,
            parameters=dump_random_model(EpisodePatchInput),
        )
        assert not db.exec(select(Episode).where(Episode.id == random_uuid)).first()

    def test_update_episode_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user_1.id)
        original_episode = episode.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            detail="Episode not found",
            headers=user_2.headers,
            parameters=dump_random_model(EpisodePatchInput),
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)

    def test_update_episode_unowned_season(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db)
        original_episode = episode.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            detail="Episode not found",
            headers=user.headers,
            parameters=dump_random_model(EpisodePatchInput),
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)

    def test_update_episode_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user.id)
        original_episode = episode.model_dump(mode="json")

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            parameters=dump_random_model(EpisodePatchInput),
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)


class TestDeleteEpisode:
    def test_delete_episode(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user.id)

        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            message="Episode deleted successfully",
            headers=user.headers,
        )
        assert not db.exec(select(Episode).where(Episode.id == episode.id)).first()

    def test_delete_episode_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        episode_id = uuid.uuid4()

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/episodes/{episode_id}",
            detail="Episode not found",
            headers=user.headers,
        )
        assert not db.exec(select(Episode).where(Episode.id == episode_id)).first()

    def test_delete_episode_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user_1.id)
        original_episode = episode.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            detail="Episode not found",
            headers=user_2.headers,
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)

    def test_delete_episode_unowned_season(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db)
        original_episode = episode.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
            detail="Episode not found",
            headers=user.headers,
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)

    def test_delete_episode_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        episode = get_random_episode(db, user_id=user.id)
        original_episode = episode.model_dump(mode="json")
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/episodes/{episode.id}",
        )
        assert_saved_to_db(db, Episode, episode.id, original_episode)
