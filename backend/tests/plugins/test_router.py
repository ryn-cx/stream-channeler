import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginInput,
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
)
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.old_tests.utils.media import create_random_plugin
from tests.old_tests.utils.test_assertions import assert_saved_to_db, assert_success
from tests.old_tests.utils.user import create_random_user_alt
from tests.old_tests.utils.utils import (
    build_random_model,
    dump_random_model,
    random_lower_string,
)
from tests.utils.media_router import (
    BaseCreateTests,
    BaseDeleteTests,
    BaseGetTests,
    BaseTests,
    BaseUpdateTests,
)


class PluginTestMixin(BaseTests):
    has_parent = False
    database_model = Plugin
    input_schema = PluginPostInput
    output_model = PluginOutput
    patch_model = PluginPatchInput
    endpoint_name = "plugins"
    model_name = "Plugin"

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | User | None = None,
    ) -> Plugin:
        return create_random_plugin(db, user_id=user_id)


class TestCreatePlugin(PluginTestMixin, BaseCreateTests):
    def test_create_shared_key_different_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        existing = create_random_plugin(db, user_id=user_1.id)
        original = existing.model_dump(mode="json")

        parameters = dump_random_model(self.input_schema, key=existing.key)
        created = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}",
            output_model=self.output_model,
            headers=user_2.headers,
            parameters=parameters,
        )
        assert_saved_to_db(db, self.database_model, created.id, parameters)
        assert_saved_to_db(db, self.database_model, existing.id, original)

    def test_create_shared_key_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        existing = create_random_plugin(db)
        original = existing.model_dump(mode="json")

        parameters = dump_random_model(self.input_schema, key=existing.key)
        created = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}",
            output_model=self.output_model,
            headers=user.headers,
            parameters=parameters,
        )
        assert_saved_to_db(db, self.database_model, created.id, parameters)
        assert_saved_to_db(db, self.database_model, existing.id, original)


class TestUpdatePlugin(PluginTestMixin, BaseUpdateTests):
    def test_update_shared_key_different_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        shared_key = random_lower_string()

        plugin_input_1 = build_random_model(PluginInput, key=shared_key)
        plugin_input_1.user_id = user_1.id
        plugin_1 = plugin_input_1.upsert(db, None)

        plugin_input_2 = build_random_model(PluginInput, key=shared_key)
        plugin_input_2.user_id = user_2.id
        plugin_2 = plugin_input_2.upsert(db, None)
        db.commit()

        original_1 = plugin_1.model_dump(mode="json")
        original_2 = plugin_2.model_dump(mode="json")

        update_data = dump_random_model(self.patch_model)
        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{plugin_1.id}",
            output_model=self.output_model,
            headers=user_1.headers,
            parameters=update_data,
        )
        assert_saved_to_db(
            db,
            self.database_model,
            plugin_1.id,
            original_1 | update_data,
            updated=True,
        )
        assert_saved_to_db(db, self.database_model, plugin_2.id, original_2)

    def test_update_shared_key_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        shared_key = random_lower_string()

        unowned_input = build_random_model(PluginInput, key=shared_key, user_id=None)
        unowned = unowned_input.upsert(db, None)

        owned_input = build_random_model(PluginInput, key=shared_key)
        owned_input.user_id = user.id
        owned = owned_input.upsert(db, None)
        db.commit()

        original_owned = owned.model_dump(mode="json")
        original_unowned = unowned.model_dump(mode="json")

        update_data = dump_random_model(self.patch_model)
        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{owned.id}",
            output_model=self.output_model,
            headers=user.headers,
            parameters=update_data,
        )
        assert_saved_to_db(
            db,
            self.database_model,
            owned.id,
            original_owned | update_data,
            updated=True,
        )
        assert_saved_to_db(db, self.database_model, unowned.id, original_unowned)


class TestGetPlugin(PluginTestMixin, BaseGetTests):
    pass


class TestDeletePlugin(PluginTestMixin, BaseDeleteTests):
    pass
