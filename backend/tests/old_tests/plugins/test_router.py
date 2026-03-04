from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
    PluginsListOutput,
)
from tests.old_tests.utils.media import (
    create_random_plugin,
)
from tests.old_tests.utils.test_assertions import (
    assert_delete,
    assert_not_authenticated,
    assert_not_found,
    assert_saved_to_db,
    assert_success,
)
from tests.old_tests.utils.user import create_random_user_alt
from tests.old_tests.utils.utils import dump_random_model, random_lower_string


class TestCreatePlugin:
    def test_create_plugin(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(PluginPostInput)
        content = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/plugins/",
            output_model=PluginOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(db, Plugin, content.id, data)

    def test_create_plugin_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        key = random_lower_string()

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/plugins/",
            parameters=dump_random_model(PluginPostInput, key=key),
        )
        assert not db.exec(select(Plugin).where(Plugin.key == key)).first()


class TestListPlugins:
    def test_list_plugins(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        create_random_plugin(db, user.id)
        create_random_plugin(db, user.id)

        response = client.get(
            f"{settings.API_V1_STR}/plugins/",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = PluginsListOutput.model_validate(response.json())
        assert content.count == 2

    def test_list_plugins_empty(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        response = client.get(
            f"{settings.API_V1_STR}/plugins/",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = PluginsListOutput.model_validate(response.json())
        assert content.count == 0

    def test_list_plugins_user_isolation(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        create_random_plugin(db, user_1.id)

        response = client.get(
            f"{settings.API_V1_STR}/plugins/",
            headers=user_2.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = PluginsListOutput.model_validate(response.json())
        assert content.count == 0

    def test_list_plugins_not_authenticated(self, client: TestClient) -> None:
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/plugins/",
        )


class TestUpdatePlugin:
    def test_update_plugin(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)
        data = dump_random_model(PluginPatchInput)

        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            output_model=PluginOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(
            db,
            Plugin,
            plugin.id,
            plugin.model_dump(mode="json") | data,
            updated=True,
        )

    def test_update_plugin_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_key = random_lower_string()

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/plugins/{random_key}",
            detail="Plugin not found",
            headers=user.headers,
            parameters=dump_random_model(PluginPatchInput),
        )
        assert not db.exec(select(Plugin).where(Plugin.key == random_key)).first()

    def test_update_plugin_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user_1.id)
        original_plugin = plugin.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            detail="Plugin not found",
            headers=user_2.headers,
            parameters=dump_random_model(PluginPatchInput),
        )
        assert_saved_to_db(db, Plugin, plugin.id, original_plugin)

    def test_update_plugin_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db)
        original_plugin = plugin.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            detail="Plugin not found",
            headers=user.headers,
            parameters=dump_random_model(PluginPatchInput),
        )
        assert_saved_to_db(db, Plugin, plugin.id, original_plugin)

    def test_update_plugin_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)
        original_plugin = plugin.model_dump(mode="json")

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            parameters=dump_random_model(PluginPatchInput),
        )
        assert_saved_to_db(db, Plugin, plugin.id, original_plugin)


class TestDeletePlugin:
    def test_delete_plugin(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)

        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            message="Plugin deleted successfully",
            headers=user.headers,
        )
        assert not db.exec(select(Plugin).where(Plugin.id == plugin.id)).first()

    def test_delete_plugin_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_key = random_lower_string()

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/plugins/{random_key}",
            detail="Plugin not found",
            headers=user.headers,
        )
        assert not db.exec(select(Plugin).where(Plugin.key == random_key)).first()

    def test_delete_plugin_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user_1.id)
        original_plugin = plugin.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            detail="Plugin not found",
            headers=user_2.headers,
        )
        assert_saved_to_db(db, Plugin, plugin.id, original_plugin)

    def test_delete_plugin_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db)
        original_plugin = plugin.model_dump(mode="json")

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
            detail="Plugin not found",
            headers=user.headers,
        )
        assert_saved_to_db(db, Plugin, plugin.id, original_plugin)

    def test_delete_plugin_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        plugin = create_random_plugin(db, user.id)
        original_plugin = plugin.model_dump(mode="json")
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/plugins/{plugin.key}",
        )
        assert_saved_to_db(db, Plugin, plugin.id, original_plugin)
