import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from tests.old_tests.utils.media import (
    create_random_season,
    create_random_show,
)
from tests.old_tests.utils.test_assertions import (
    assert_conflict,
    assert_delete,
    assert_not_authenticated,
    assert_not_found,
    assert_saved_to_db,
    assert_success,
)
from tests.old_tests.utils.user import create_random_user_alt
from tests.old_tests.utils.utils import dump_random_model


class TestCreateSeason:
    def test_create_season(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        data = dump_random_model(SeasonPostInput, show_id=show.id)

        content = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/seasons/",
            output_model=SeasonOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(db, Season, content.id, data)

    def test_create_season_show_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/seasons/",
            detail="Show not found",
            headers=user.headers,
            parameters=dump_random_model(SeasonPostInput, show_id=uuid.uuid4()),
        )

    def test_create_season_duplicate_key(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user.id)
        original_season = season.model_dump(mode="json")

        assert_conflict(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/seasons/",
            detail="Season with this key already exists",
            headers=user.headers,
            parameters=dump_random_model(
                SeasonPostInput,
                show_id=season.show_id,
                key=season.key,
            ),
        )
        assert_saved_to_db(db, Season, season.id, original_season)

    def test_create_season_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user_1.id)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/seasons/",
            detail="Show not found",
            headers=user_2.headers,
            parameters=dump_random_model(SeasonPostInput, show_id=show.id),
        )
        seasons = db.exec(select(Season).where(Season.show_id == show.id)).all()
        assert len(seasons) == 0

    def test_create_season_unowned_show(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/seasons/",
            detail="Show not found",
            headers=user.headers,
            parameters=dump_random_model(SeasonPostInput, show_id=show.id),
        )
        seasons = db.exec(select(Season).where(Season.show_id == show.id)).all()
        assert len(seasons) == 0

    def test_create_season_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/seasons/",
            parameters=dump_random_model(SeasonPostInput, show_id=show.id),
        )
        seasons = db.exec(select(Season).where(Season.show_id == show.id)).all()
        assert len(seasons) == 0


class TestListSeasonsFromShow:
    def test_list_seasons_from_show(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user.id)

        response = client.get(
            f"{settings.API_V1_STR}/shows/{season.show_id}/seasons",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = SeasonsListOutput.model_validate(response.json())
        assert content.count == 1

    def test_list_seasons_from_show_empty(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)

        response = client.get(
            f"{settings.API_V1_STR}/shows/{show.id}/seasons",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = SeasonsListOutput.model_validate(response.json())
        assert content.count == 0

    def test_list_seasons_from_show_multiple(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        create_random_season(db, show=show)
        create_random_season(db, show=show)

        response = client.get(
            f"{settings.API_V1_STR}/shows/{show.id}/seasons",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = SeasonsListOutput.model_validate(response.json())
        assert content.count == 2

    def test_list_seasons_from_show_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/shows/{uuid.uuid4()}/seasons",
            detail="Show not found",
            headers=user.headers,
        )

    def test_list_seasons_from_show_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user_1.id)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/shows/{show.id}/seasons",
            detail="Show not found",
            headers=user_2.headers,
        )

    def test_list_seasons_from_show_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/shows/{show.id}/seasons",
            detail="Show not found",
            headers=user.headers,
        )

    def test_list_seasons_from_show_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/shows/{show.id}/seasons",
        )


class TestUpdateSeason:
    def test_update_season(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user.id)
        data = dump_random_model(SeasonPatchInput)

        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            output_model=SeasonOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(
            db,
            Season,
            season.id,
            season.model_dump(mode="json") | data,
            updated=True,
        )

    def test_update_season_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_uuid = uuid.uuid4()

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/seasons/{random_uuid}",
            detail="Season not found",
            headers=user.headers,
            parameters=dump_random_model(SeasonPatchInput),
        )
        assert not db.exec(select(Season).where(Season.id == random_uuid)).first()

    def test_update_season_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user_1.id)
        original_season = season.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            detail="Season not found",
            headers=user_2.headers,
            parameters=dump_random_model(SeasonPatchInput),
        )
        assert_saved_to_db(db, Season, season.id, original_season)

    def test_update_season_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db)
        original_season = season.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            detail="Season not found",
            headers=user.headers,
            parameters=dump_random_model(SeasonPatchInput),
        )
        assert_saved_to_db(db, Season, season.id, original_season)

    def test_update_season_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user.id)
        original_season = season.model_dump(mode="json")

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            parameters=dump_random_model(SeasonPatchInput),
        )
        assert_saved_to_db(db, Season, season.id, original_season)


class TestDeleteSeason:
    def test_delete_season(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user.id)

        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            message="Season deleted successfully",
            headers=user.headers,
        )
        assert not db.exec(select(Season).where(Season.id == season.id)).first()

    def test_delete_season_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        season_id = uuid.uuid4()

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/seasons/{season_id}",
            detail="Season not found",
            headers=user.headers,
        )
        assert not db.exec(select(Season).where(Season.id == season_id)).first()

    def test_delete_season_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user_1.id)
        original_season = season.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            detail="Season not found",
            headers=user_2.headers,
        )
        assert_saved_to_db(db, Season, season.id, original_season)

    def test_delete_season_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db)
        original_season = season.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
            detail="Season not found",
            headers=user.headers,
        )
        assert_saved_to_db(db, Season, season.id, original_season)

    def test_delete_season_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        season = create_random_season(db, user_id=user.id)
        original_season = season.model_dump(mode="json")
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/seasons/{season.id}",
        )
        assert_saved_to_db(db, Season, season.id, original_season)
