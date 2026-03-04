import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
    ShowPostInput,
    ShowsListOutput,
)
from tests.old_tests.utils.media import (
    create_random_show,
    create_random_source,
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


class TestCreateShow:
    def test_create_show(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        data = dump_random_model(ShowPostInput, source_id=source.id)

        content = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/shows/",
            output_model=ShowOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(db, Show, content.id, data)

    def test_create_show_source_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/shows/",
            detail="Source not found",
            headers=user.headers,
            parameters=dump_random_model(ShowPostInput, source_id=uuid.uuid4()),
        )

    def test_create_show_duplicate_key(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        original_show = show.model_dump(mode="json")

        assert_conflict(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/shows/",
            detail="Show with this key already exists",
            headers=user.headers,
            parameters=dump_random_model(
                ShowPostInput,
                source_id=show.source_id,
                key=show.key,
            ),
        )
        assert_saved_to_db(db, Show, show.id, original_show)

    def test_create_show_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user_1.id)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/shows/",
            detail="Source not found",
            headers=user_2.headers,
            parameters=dump_random_model(ShowPostInput, source_id=source.id),
        )
        shows = db.exec(select(Show).where(Show.source_id == source.id)).all()
        assert len(shows) == 0

    def test_create_show_unowned_source(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/shows/",
            detail="Source not found",
            headers=user.headers,
            parameters=dump_random_model(ShowPostInput, source_id=source.id),
        )
        shows = db.exec(select(Show).where(Show.source_id == source.id)).all()
        assert len(shows) == 0

    def test_create_show_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/shows/",
            parameters=dump_random_model(ShowPostInput, source_id=source.id),
        )
        shows = db.exec(select(Show).where(Show.source_id == source.id)).all()
        assert len(shows) == 0


class TestListShowsFromSource:
    def test_list_shows_from_source(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)

        response = client.get(
            f"{settings.API_V1_STR}/sources/{show.source_id}/shows",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = ShowsListOutput.model_validate(response.json())
        assert content.count == 1

    def test_list_shows_from_source_empty(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)

        response = client.get(
            f"{settings.API_V1_STR}/sources/{source.id}/shows",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = ShowsListOutput.model_validate(response.json())
        assert content.count == 0

    def test_list_shows_from_source_multiple(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        create_random_show(db, source=source)
        create_random_show(db, source=source)

        response = client.get(
            f"{settings.API_V1_STR}/sources/{source.id}/shows",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = ShowsListOutput.model_validate(response.json())
        assert content.count == 2

    def test_list_shows_from_source_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/sources/{uuid.uuid4()}/shows",
            detail="Source not found",
            headers=user.headers,
        )

    def test_list_shows_from_source_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user_1.id)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/sources/{source.id}/shows",
            detail="Source not found",
            headers=user_2.headers,
        )

    def test_list_shows_from_source_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/sources/{source.id}/shows",
            detail="Source not found",
            headers=user.headers,
        )

    def test_list_shows_from_source_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/sources/{source.id}/shows",
        )


class TestUpdateShow:
    def test_update_show(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        data = dump_random_model(ShowPatchInput)

        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            output_model=ShowOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(
            db,
            Show,
            show.id,
            show.model_dump(mode="json") | data,
            updated=True,
        )

    def test_update_show_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_uuid = uuid.uuid4()

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/shows/{random_uuid}",
            detail="Show not found",
            headers=user.headers,
            parameters=dump_random_model(ShowPatchInput),
        )
        assert not db.exec(select(Show).where(Show.id == random_uuid)).first()

    def test_update_show_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user_1.id)
        original_show = show.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            detail="Show not found",
            headers=user_2.headers,
            parameters=dump_random_model(ShowPatchInput),
        )
        assert_saved_to_db(db, Show, show.id, original_show)

    def test_update_show_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db)
        original_show = show.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            detail="Show not found",
            headers=user.headers,
            parameters=dump_random_model(ShowPatchInput),
        )
        assert_saved_to_db(db, Show, show.id, original_show)

    def test_update_show_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        original_show = show.model_dump(mode="json")

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            parameters=dump_random_model(ShowPatchInput),
        )
        assert_saved_to_db(db, Show, show.id, original_show)


class TestDeleteShow:
    def test_delete_show(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)

        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            message="Show deleted successfully",
            headers=user.headers,
        )
        assert not db.exec(select(Show).where(Show.id == show.id)).first()

    def test_delete_show_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        show_id = uuid.uuid4()

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/shows/{show_id}",
            detail="Show not found",
            headers=user.headers,
        )
        assert not db.exec(select(Show).where(Show.id == show_id)).first()

    def test_delete_show_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user_1.id)
        original_show = show.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            detail="Show not found",
            headers=user_2.headers,
        )
        assert_saved_to_db(db, Show, show.id, original_show)

    def test_delete_show_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db)
        original_show = show.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
            detail="Show not found",
            headers=user.headers,
        )
        assert_saved_to_db(db, Show, show.id, original_show)

    def test_delete_show_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        show = create_random_show(db, user_id=user.id)
        original_show = show.model_dump(mode="json")
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/shows/{show.id}",
        )
        assert_saved_to_db(db, Show, show.id, original_show)
