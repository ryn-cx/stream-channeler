# TODO: Validate
from __future__ import annotations

import dataclasses
import uuid
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from tests.utils.route_assertions import Method

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

from app.channels.models import Channel
from app.channels.schemas import ChannelOutput, ChannelPatchInput, ChannelPostInput
from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput, PluginPatchInput, PluginPostInput
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.models import Show
from app.shows.schemas import ShowOutput, ShowPatchInput, ShowPostInput, ShowsListOutput
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from app.watches.models import Watch
from app.watches.schemas import WatchOutput, WatchPatchInput, WatchPostInput
from tests.users.utils import CreatedUser, create_random_user_alt
from tests.utils.route_assertions import assert_forbidden, assert_not_authenticated

SUPPORTED_MODELS = Channel | Episode | Season | Show | Source | Plugin | Watch

INPUT_SCHEMAS = (
    ChannelPostInput
    | EpisodePostInput
    | PluginPostInput
    | SeasonPostInput
    | ShowPostInput
    | SourcePostInput
    | WatchPostInput
)
OUTPUT_MODELS = (
    ChannelOutput
    | EpisodeOutput
    | PluginOutput
    | SeasonOutput
    | ShowOutput
    | SourceOutput
    | WatchOutput
)
LIST_OUTPUT_MODELS = (
    EpisodesListOutput | SeasonsListOutput | ShowsListOutput | SourcesListOutput
)
PATCH_MODELS = (
    ChannelPatchInput
    | EpisodePatchInput
    | PluginPatchInput
    | SeasonPatchInput
    | ShowPatchInput
    | SourcePatchInput
    | WatchPatchInput
)
OUTPUT_MODELS_WITH_KEY = (
    EpisodeOutput | PluginOutput | SeasonOutput | ShowOutput | SourceOutput
)
MODELS_WITH_KEY = Episode | Plugin | Season | Show | Source
MODELS_WITH_PARENT = Episode | Season | Show | Source
MODELS_REQUIRING_USER = Channel


def _pluralize(name: str) -> str:
    if name.endswith(("ch", "sh", "s", "x", "z")):
        return name + "es"
    return name + "s"


def _get_foreign_keys(model: type[SQLModel]) -> list[str]:
    return [
        field_name
        for field_name, field_info in model.model_fields.items()
        if isinstance(getattr(field_info, "foreign_key", None), str)
        and field_name != "user_id"
    ]


@dataclasses.dataclass
class CreatedTestData[T]:
    record: T
    user: CreatedUser
    headers: dict[str, str]


class BaseTests[T: SUPPORTED_MODELS]:
    database_model: type[T]
    input_schema: type[INPUT_SCHEMAS]
    output_model: type[OUTPUT_MODELS]
    list_output_model: type[LIST_OUTPUT_MODELS]
    patch_model: type[PATCH_MODELS]
    create_parent_function: Callable[..., Plugin | Source | Show | Season | Episode]
    create_record_function: Callable[..., T]
    supports_unowned_records: bool = True

    @property
    def has_parent(self) -> bool:
        return len(_get_foreign_keys(self.database_model)) > 0

    @property
    def parent_key_name(self) -> str:
        keys = _get_foreign_keys(self.database_model)
        if len(keys) == 0:
            msg = f"Model {self.model_name} does not have a parent key"
            raise ValueError(msg)
        if len(keys) > 1:
            msg = f"Model {self.model_name} has multiple parent keys: {keys}"
            raise ValueError(msg)
        return keys[0]

    @property
    def model_name(self) -> str:
        return self.database_model.__name__

    @property
    def endpoint_name(self) -> str:
        return _pluralize(self.database_model.__name__.lower())

    @property
    def parent_name(self) -> str:
        return self.parent_key_name.removesuffix("_id").capitalize()

    @property
    def parent_endpoint_name(self) -> str:
        return _pluralize(self.parent_name.lower())

    def entry_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{record_id}"

    @contextmanager
    def assert_no_db_change(self, db: Session) -> Generator[None]:
        """Assert that no records were added, removed, or modified."""
        records_before = db.exec(select(self.database_model)).all()
        yield
        records_after = db.exec(select(self.database_model)).all()
        assert records_before == records_after

    def assert_only_record_changed(
        self,
        db: Session,
        record_id: uuid.UUID,
        records_before: Sequence[T],
    ) -> None:
        """Assert only the given record changed; all others are identical."""
        updated_record = db.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).one()
        expected = sorted(
            [r if r.id != record_id else updated_record for r in records_before],
            key=lambda r: r.id,
        )
        actual = sorted(
            db.exec(select(self.database_model)).all(),
            key=lambda r: r.id,
        )
        assert expected == actual

    def assert_only_record_added(
        self,
        db: Session,
        record_id: uuid.UUID,
        records_before: Sequence[T],
    ) -> None:
        """Assert one record was added and all existing records are unchanged."""
        new_record = db.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).one()
        expected = sorted([*records_before, new_record], key=lambda r: r.id)
        actual = sorted(
            db.exec(select(self.database_model)).all(),
            key=lambda r: r.id,
        )
        assert expected == actual

    @staticmethod
    def get_plugin(record: SUPPORTED_MODELS) -> Plugin | None:
        while not isinstance(record, Plugin):
            keys = _get_foreign_keys(type(record))
            if not keys:
                return None
            record = getattr(record, keys[0].removesuffix("_id"))
        return record

    def set_visibility(
        self,
        db: Session,
        record: SUPPORTED_MODELS,
        *,
        public: bool,
    ) -> None:
        plugin = self.get_plugin(record)
        if plugin is not None:
            plugin.public = public
        else:
            record.public = public  # type: ignore[union-attr]
        db.flush()

    def create_test_data(
        self,
        client: TestClient,
        db: Session,
        relationship: str,
        *,
        authenticated: bool = True,
        public: bool = True,
    ) -> CreatedTestData[T]:
        """Create a user and record with the given ownership and visibility."""
        if relationship == "unowned" and not self.supports_unowned_records:
            pytest.skip("Model does not support unowned records")

        user = create_random_user_alt(client, db)
        other = create_random_user_alt(client, db)

        match relationship:
            case "owner":
                record = self.create_record_function(db, user_id=user.id)
            case "other_owner":
                record = self.create_record_function(db, user_id=other.id)
            case _:
                record = self.create_record_function(db)

        # Populate with random dummy data to make sure filtering works correctly.
        self.create_record_function(db, user_id=user.id)
        self.create_record_function(db, user_id=other.id)
        if not isinstance(record, MODELS_REQUIRING_USER):
            self.create_record_function(db)

        self.set_visibility(db, record, public=public)
        headers = user.headers if authenticated else {}
        return CreatedTestData(record=record, user=user, headers=headers)

    def assert_write_permission(  # noqa: PLR0913
        self,
        db: Session,
        client: TestClient,
        *,
        authenticated: bool,
        model_type: str,
        method: Method,
        url: str,
        detail: str,
        headers: dict[str, str],
        parameters: dict[str, Any] | list[Any] | None = None,
    ) -> bool:
        """Assert permission denied for write operations. Returns True for success."""
        if not authenticated:
            with self.assert_no_db_change(db):
                assert_not_authenticated(
                    client=client,
                    method=method,
                    url=url,
                    parameters=parameters,
                )
            return False
        if model_type != "owner":
            with self.assert_no_db_change(db):
                assert_forbidden(
                    client=client,
                    method=method,
                    url=url,
                    detail=detail,
                    headers=headers,
                    parameters=parameters,
                )
            return False
        return True

    def assert_read_permission(  # noqa: PLR0913
        self,
        client: TestClient,
        *,
        authenticated: bool,
        model_type: str,
        public: bool,
        method: Method,
        url: str,
        detail: str,
        headers: dict[str, str],
    ) -> bool:
        """Assert permission denied for read operations. Returns True for success."""
        if not authenticated and not public:
            assert_not_authenticated(client=client, method=method, url=url)
            return False
        if not authenticated or model_type == "owner" or public:
            return True
        assert_forbidden(
            client=client,
            method=method,
            url=url,
            detail=detail,
            headers=headers,
        )
        return False
