import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.models import MetadataMixin, TimestampIdMixin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
    PluginsListOutput,
)
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
    ShowPostInput,
    ShowsListOutput,
)
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from app.users.models import User
from app.watches.models import Watch
from app.watches.schemas import (
    WatchesListOutput,
    WatchOutput,
    WatchPatchInput,
    WatchPostInput,
)
from tests.old_tests.utils.test_assertions import (
    assert_conflict,
    assert_delete,
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
    assert_saved_to_db,
    assert_success,
)
from tests.users.utils import create_random_user_alt
from tests.utils.utils import dump_random_model


class BaseTests:
    has_parent: bool
    database_model: type[Episode | Season | Show | Source | Plugin | Watch]
    input_schema: type[
        EpisodePostInput
        | SeasonPostInput
        | ShowPostInput
        | SourcePostInput
        | PluginPostInput
        | WatchPostInput
    ]
    output_model: type[
        EpisodeOutput
        | SeasonOutput
        | ShowOutput
        | SourceOutput
        | PluginOutput
        | WatchOutput
    ]
    patch_model: type[
        EpisodePatchInput
        | SeasonPatchInput
        | ShowPatchInput
        | SourcePatchInput
        | PluginPatchInput
        | WatchPatchInput
    ]
    list_output_model: type[
        EpisodesListOutput
        | SeasonsListOutput
        | ShowsListOutput
        | SourcesListOutput
        | PluginsListOutput
        | WatchesListOutput
    ]
    endpoint_name: str
    parent_endpoint_name: str
    parent_key_name: str
    model_name: str
    parent_name: str

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> Plugin | Source | Show | Season | User | Episode:
        """Create a parent record."""
        raise NotImplementedError

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | Episode | User | Watch | None = None,
    ) -> MetadataMixin | TimestampIdMixin:
        """Create a record."""
        raise NotImplementedError

    def _create_url(self, parent_id: uuid.UUID | str | None = None) -> str:
        """Build the URL for create endpoints."""
        if self.has_parent and parent_id is not None:
            return f"{settings.API_V1_STR}/{self.parent_endpoint_name}/{parent_id}/{self.endpoint_name}"
        return f"{settings.API_V1_STR}/{self.endpoint_name}"

    def assert_entry_not_in_db(self, db: Session, record_id: uuid.UUID | str) -> None:
        """Assert that no record with the given identifier exists in the database."""
        assert not db.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).first()


class BaseCreateTests(BaseTests):
    @pytest.mark.parametrize("mode", ["full", "minimal"])
    def test_create(
        self,
        client: TestClient,
        db: Session,
        mode: str,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent_id = None
        if self.has_parent:
            parent = self.create_parent(db, user_id=user.id)
            parent_id = parent.id
        parameters = dump_random_model(self.input_schema, mode=mode)

        content = assert_success(
            client=client,
            method="post",
            url=self._create_url(parent_id),
            output_model=self.output_model,
            headers=user.headers,
            parameters=parameters,
        )
        assert_saved_to_db(db, self.database_model, content.id, parameters)

    def test_create_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        assert issubclass(self.database_model, MetadataMixin)  # Type narrowing

        user = create_random_user_alt(client, db)
        parent_id = None
        if self.has_parent:
            parent = self.create_parent(db, user_id=user.id)
            parent_id = parent.id
        key = str(uuid.uuid4())
        parameters = dump_random_model(self.input_schema, key=key)

        assert_not_authenticated(
            client=client,
            method="post",
            url=self._create_url(parent_id),
            parameters=parameters,
        )

        record = db.exec(
            select(self.database_model).where(self.database_model.key == key),
        ).first()
        assert record is None

    def test_create_parent_not_found(self, client: TestClient, db: Session) -> None:
        if not self.has_parent:
            pytest.skip()

        user = create_random_user_alt(client, db)
        parameters = dump_random_model(self.input_schema)

        assert_not_found(
            client=client,
            method="post",
            url=self._create_url(str(uuid.uuid4())),
            detail=f"{self.parent_name} not found",
            headers=user.headers,
            parameters=parameters,
        )

    def test_create_duplicate_key(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        if not self.has_parent:
            pytest.skip()

        user = create_random_user_alt(client, db)
        record = self.create_record(db, user_id=user.id)
        assert isinstance(record, MetadataMixin)  # Type narrowing
        original_record = record.model_dump(mode="json")

        parent_id = getattr(record, self.parent_key_name)
        parameters = dump_random_model(self.input_schema, key=record.key)

        assert_conflict(
            client=client,
            method="post",
            url=self._create_url(parent_id),
            detail=f"{self.model_name} with this key already exists",
            headers=user.headers,
            parameters=parameters,
        )
        assert_saved_to_db(db, self.database_model, record.id, original_record)

    def test_create_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        if not self.has_parent:
            pytest.skip()

        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user_1.id)

        parameters = dump_random_model(self.input_schema)

        assert_forbidden(
            client=client,
            method="post",
            url=self._create_url(parent.id),
            detail=f"Not authorized to access this {self.parent_name}",
            headers=user_2.headers,
            parameters=parameters,
        )
        parent_column = getattr(self.database_model, self.parent_key_name)
        records = db.exec(
            select(self.database_model).where(parent_column == parent.id),
        ).all()
        assert len(records) == 0

    def test_create_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        if not self.has_parent:
            pytest.skip()

        parent = self.create_parent(db)
        user = create_random_user_alt(client, db)

        parameters = dump_random_model(self.input_schema)

        assert_forbidden(
            client=client,
            method="post",
            url=self._create_url(parent.id),
            detail=f"Not authorized to access this {self.parent_name}",
            headers=user.headers,
            parameters=parameters,
        )
        parent_column = getattr(self.database_model, self.parent_key_name)
        records = db.exec(
            select(self.database_model).where(parent_column == parent.id),
        ).all()
        assert len(records) == 0


class BaseListFromParentTests(BaseTests):
    def _parent_url(self, parent_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/{self.parent_endpoint_name}/{parent_id}/{self.endpoint_name}"

    def test_list_from_parent(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user.id)
        self.create_record(db, parent=parent)

        response = client.get(
            self._parent_url(parent.id),
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        self.list_output_model.model_validate(response.json())
        assert response.json()["count"] == 1

    def test_list_from_parent_empty(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user.id)

        response = client.get(
            self._parent_url(parent.id),
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        self.list_output_model.model_validate(response.json())
        assert response.json()["count"] == 0

    def test_list_from_parent_filters_by_parent(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user.id)
        other_parent = self.create_parent(db, user_id=user.id)
        self.create_record(db, parent=parent)
        self.create_record(db, parent=other_parent)

        response = client.get(
            self._parent_url(parent.id),
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        self.list_output_model.model_validate(response.json())
        assert response.json()["count"] == 1

    def test_list_from_parent_multiple(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user.id)
        self.create_record(db, parent=parent)
        self.create_record(db, parent=parent)

        response = client.get(
            self._parent_url(parent.id),
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        self.list_output_model.model_validate(response.json())
        assert response.json()["count"] == 2

    def test_list_from_parent_not_found(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=self._parent_url(str(uuid.uuid4())),
            detail=f"{self.parent_name} not found",
            headers=user.headers,
        )

    def test_list_from_parent_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user_1.id)

        assert_forbidden(
            client=client,
            method="get",
            url=self._parent_url(parent.id),
            detail=f"Not authorized to access this {self.parent_name}",
            headers=user_2.headers,
        )

    def test_list_from_parent_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db)

        assert_forbidden(
            client=client,
            method="get",
            url=self._parent_url(parent.id),
            detail=f"Not authorized to access this {self.parent_name}",
            headers=user.headers,
        )

    def test_list_from_parent_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent = self.create_parent(db, user_id=user.id)
        assert_not_authenticated(
            client=client,
            method="get",
            url=self._parent_url(parent.id),
        )


class BaseGetTests(BaseTests):
    def _entry_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{record_id}"

    def test_get(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user.id)

        response = client.get(
            self._entry_url(entry.id),
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        self.output_model.model_validate(response.json())

    def test_get_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=self._entry_url(str(uuid.uuid4())),
            detail=f"{self.model_name} not found",
            headers=user.headers,
        )

    def test_get_wrong_user(self, client: TestClient, db: Session) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user_1.id)

        assert_forbidden(
            client=client,
            method="get",
            url=self._entry_url(entry.id),
            detail=f"Not authorized to access this {self.model_name}",
            headers=user_2.headers,
        )

    def test_get_unowned(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db)

        assert_forbidden(
            client=client,
            method="get",
            url=self._entry_url(entry.id),
            detail=f"Not authorized to access this {self.model_name}",
            headers=user.headers,
        )

    def test_get_not_authenticated(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user.id)
        assert_not_authenticated(
            client=client,
            method="get",
            url=self._entry_url(entry.id),
        )


class BaseUpdateTests(BaseTests):
    @pytest.mark.parametrize(
        ("create_mode", "update_mode"),
        [
            ("minimal", "minimal"),
            ("minimal", "full"),
            ("full", "minimal"),
            ("full", "full"),
        ],
    )
    def test_update(
        self,
        client: TestClient,
        db: Session,
        create_mode: str,
        update_mode: str,
    ) -> None:
        user = create_random_user_alt(client, db)
        parent_id = None
        if self.has_parent:
            parent = self.create_parent(db, user_id=user.id)
            parent_id = parent.id

        create_data = dump_random_model(self.input_schema, mode=create_mode)
        created = assert_success(
            client=client,
            method="post",
            url=self._create_url(parent_id),
            output_model=self.output_model,
            headers=user.headers,
            parameters=create_data,
        )

        update_data = dump_random_model(self.patch_model, mode=update_mode)
        assert_success(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{created.id}",  # type: ignore[arg-type]
            output_model=self.output_model,
            headers=user.headers,
            parameters=update_data,
        )
        assert_saved_to_db(
            db,
            self.database_model,
            created.id,
            created.model_dump(mode="json") | update_data,
            updated=True,
        )

    def test_update_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_uuid = str(uuid.uuid4())

        assert_not_found(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{random_uuid}",
            detail=f"{self.model_name} not found",
            headers=user.headers,
            parameters=dump_random_model(self.patch_model),
        )
        self.assert_entry_not_in_db(db, random_uuid)

    def test_update_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user_1.id)
        original = entry.model_dump(mode="json")

        assert_forbidden(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
            detail=f"Not authorized to access this {self.model_name}",
            headers=user_2.headers,
            parameters=dump_random_model(self.patch_model),
        )
        assert_saved_to_db(db, self.database_model, entry.id, original)

    def test_update_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db)
        original = entry.model_dump(mode="json")

        assert_forbidden(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
            detail=f"Not authorized to access this {self.model_name}",
            headers=user.headers,
            parameters=dump_random_model(self.patch_model),
        )
        assert_saved_to_db(db, self.database_model, entry.id, original)

    def test_update_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user.id)
        original = entry.model_dump(mode="json")

        assert_not_authenticated(
            client=client,
            method="patch",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
            parameters=dump_random_model(self.patch_model),
        )
        assert_saved_to_db(db, self.database_model, entry.id, original)


class BaseDeleteTests(BaseTests):
    def test_delete(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user.id)

        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
            message=f"{self.model_name} deleted successfully",
            headers=user.headers,
        )
        assert not db.exec(
            select(self.database_model).where(self.database_model.id == entry.id),
        ).first()

    def test_delete_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        random_id = str(uuid.uuid4())

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{random_id}",
            detail=f"{self.model_name} not found",
            headers=user.headers,
        )
        self.assert_entry_not_in_db(db, random_id)

    def test_delete_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user_1.id)
        original = entry.model_dump(mode="json")

        assert_forbidden(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
            detail=f"Not authorized to access this {self.model_name}",
            headers=user_2.headers,
        )
        assert_saved_to_db(db, self.database_model, entry.id, original)

    def test_delete_unowned(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db)
        original = entry.model_dump(mode="json")

        assert_forbidden(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
            detail=f"Not authorized to access this {self.model_name}",
            headers=user.headers,
        )
        assert_saved_to_db(db, self.database_model, entry.id, original)

    def test_delete_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        entry = self.create_record(db, user_id=user.id)
        original = entry.model_dump(mode="json")
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/{self.endpoint_name}/{entry.id}",
        )
        assert_saved_to_db(db, self.database_model, entry.id, original)
