import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from tests.old_tests.utils.media import (
    create_random_plugin,
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
from tests.old_tests.utils.utils import dump_random_model, random_lower_string


class TestCreateSource:
    def test_create_source(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)
        data = dump_random_model(SourcePostInput, plugin_key=plugin.key)

        content = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/sources/",
            output_model=SourceOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(db, Source, content.id, data)

    def test_create_source_plugin_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/sources/",
            detail="Plugin not found",
            headers=user.headers,
            parameters=dump_random_model(
                SourcePostInput,
                plugin_key=random_lower_string(),
            ),
        )

    def test_create_source_duplicate_key(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        original_source = source.model_dump(mode="json")

        assert_conflict(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/sources/",
            detail="Source with this key already exists",
            headers=user.headers,
            parameters=dump_random_model(
                SourcePostInput,
                plugin_key=source.plugin.key,
                key=source.key,
            ),
        )
        assert_saved_to_db(db, Source, source.id, original_source)

    def test_create_source_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user_1.id)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/sources/",
            detail="Plugin not found",
            headers=user_2.headers,
            parameters=dump_random_model(SourcePostInput, plugin_key=plugin.key),
        )
        sources = db.exec(select(Source).where(Source.plugin_id == plugin.id)).all()
        assert len(sources) == 0

    def test_create_source_unowned_plugin(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/sources/",
            detail="Plugin not found",
            headers=user.headers,
            parameters=dump_random_model(SourcePostInput, plugin_key=plugin.key),
        )
        sources = db.exec(select(Source).where(Source.plugin_id == plugin.id)).all()
        assert len(sources) == 0

    def test_create_source_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/sources/",
            parameters=dump_random_model(SourcePostInput, plugin_key=plugin.key),
        )
        sources = db.exec(select(Source).where(Source.plugin_id == plugin.id)).all()
        assert len(sources) == 0


class TestListSourcesFromPlugin:
    def test_list_sources_from_plugin(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        plugin_key = source.plugin.key

        response = client.get(
            f"{settings.API_V1_STR}/plugins/{plugin_key}/sources",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = SourcesListOutput.model_validate(response.json())
        assert content.count == 1

    def test_list_sources_from_plugin_empty(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)

        response = client.get(
            f"{settings.API_V1_STR}/plugins/{plugin.key}/sources",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = SourcesListOutput.model_validate(response.json())
        assert content.count == 0

    def test_list_sources_from_plugin_multiple(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)
        create_random_source(db, plugin=plugin)
        create_random_source(db, plugin=plugin)

        response = client.get(
            f"{settings.API_V1_STR}/plugins/{plugin.key}/sources",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = SourcesListOutput.model_validate(response.json())
        assert content.count == 2

    def test_list_sources_from_plugin_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/plugins/{random_lower_string()}/sources",
            detail="Plugin not found",
            headers=user.headers,
        )

    def test_list_sources_from_plugin_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user_1.id)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}/sources",
            detail="Plugin not found",
            headers=user_2.headers,
        )

    def test_list_sources_from_plugin_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db)

        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}/sources",
            detail="Plugin not found",
            headers=user.headers,
        )

    def test_list_sources_from_plugin_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}/sources",
        )


class TestUpdateSource:
    def test_update_source(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        data = dump_random_model(SourcePatchInput)

        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            output_model=SourceOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(
            db,
            Source,
            source.id,
            source.model_dump(mode="json") | data,
            updated=True,
        )

    def test_update_source_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_uuid = uuid.uuid4()

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/sources/{random_uuid}",
            detail="Source not found",
            headers=user.headers,
            parameters=dump_random_model(SourcePatchInput),
        )
        assert not db.exec(select(Source).where(Source.id == random_uuid)).first()

    def test_update_source_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user_1.id)
        original_source = source.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            detail="Source not found",
            headers=user_2.headers,
            parameters=dump_random_model(SourcePatchInput),
        )
        assert_saved_to_db(db, Source, source.id, original_source)

    def test_update_source_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db)
        original_source = source.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            detail="Source not found",
            headers=user.headers,
            parameters=dump_random_model(SourcePatchInput),
        )
        assert_saved_to_db(db, Source, source.id, original_source)

    def test_update_source_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        original_source = source.model_dump(mode="json")

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            parameters=dump_random_model(SourcePatchInput),
        )
        assert_saved_to_db(db, Source, source.id, original_source)


class TestDeleteSource:
    def test_delete_source(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)

        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            message="Source deleted successfully",
            headers=user.headers,
        )
        assert not db.exec(select(Source).where(Source.id == source.id)).first()

    def test_delete_source_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        source_id = uuid.uuid4()

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/sources/{source_id}",
            detail="Source not found",
            headers=user.headers,
        )
        assert not db.exec(select(Source).where(Source.id == source_id)).first()

    def test_delete_source_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user_1.id)
        original_source = source.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            detail="Source not found",
            headers=user_2.headers,
        )
        assert_saved_to_db(db, Source, source.id, original_source)

    def test_delete_source_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db)
        original_source = source.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
            detail="Source not found",
            headers=user.headers,
        )
        assert_saved_to_db(db, Source, source.id, original_source)

    def test_delete_source_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        source = create_random_source(db, user_id=user.id)
        original_source = source.model_dump(mode="json")
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/sources/{source.id}",
        )
        assert_saved_to_db(db, Source, source.id, original_source)
