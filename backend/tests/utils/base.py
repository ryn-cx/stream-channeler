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

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, col, select

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
MODELS_WITH_PARENT = Episode | Season | Show | Source | Watch


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
    returns_list: bool = False

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

    def get_parent(self, db: Session, record: T) -> SUPPORTED_MODELS:
        """Look up the parent record from the database."""

        statement = select(type(record)).where(type(record).id == record.id)
        record_from_db = db.exec(statement).one()
        assert isinstance(record_from_db, MODELS_WITH_PARENT)
        return record_from_db.parent()

    def entry_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{record_id}"

    @contextmanager
    def assert_no_db_change(self, db: Session) -> Generator[None]:
        """Assert that no records were added, removed, or modified."""
        records_before = db.exec(select(self.database_model)).all()
        yield
        records_after = db.exec(select(self.database_model)).all()
        assert records_before == records_after

    def assert_only_records_changed(
        self,
        db: Session,
        updated_record_ids: Sequence[uuid.UUID],
        records_before: Sequence[T],
    ) -> None:
        """Assert only the given records changed; all others are identical."""
        all_records_after = db.exec(select(self.database_model)).all()
        unmodified_before = sorted(
            [
                record
                for record in records_before
                if record.id not in updated_record_ids
            ],
            key=lambda record: record.id,
        )
        unmodified_after = sorted(
            [
                record
                for record in all_records_after
                if record.id not in updated_record_ids
            ],
            key=lambda record: record.id,
        )
        assert unmodified_before == unmodified_after

    def assert_only_records_added(
        self,
        db: Session,
        new_record_ids: Sequence[uuid.UUID],
        records_before: Sequence[T],
    ) -> None:
        """Assert only the given records were added and all existing records are unchanged."""
        new_records = list(
            db.exec(
                select(self.database_model).where(
                    col(self.database_model.id).in_(new_record_ids),
                ),
            ).all(),
        )

        expected = sorted([*records_before, *new_records], key=lambda r: r.id)
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
        *,
        is_owner: bool = True,
        authenticated: bool = True,
        public: bool = True,
    ) -> CreatedTestData[T]:
        """Create a user and record with the given ownership and visibility."""
        user = create_random_user_alt(client, db)
        other = create_random_user_alt(client, db)

        if is_owner:
            record = self.create_record_function(db, user_id=user.id)
        else:
            record = self.create_record_function(db, user_id=other.id)

        # Populate with random dummy data to make sure filtering works correctly.
        self.create_record_function(db, user_id=user.id)
        self.create_record_function(db, user_id=other.id)

        self.set_visibility(db, record, public=public)
        headers = user.headers if authenticated else {}
        return CreatedTestData(record=record, user=user, headers=headers)

    def assert_write_permission(  # noqa: PLR0913
        self,
        db: Session,
        client: TestClient,
        *,
        authenticated: bool,
        is_owner: bool,
        public: bool = False,
        method: Method,
        url: str,
        detail: str,
        headers: dict[str, str],
        parameters: dict[str, Any] | list[Any] | None = None,
    ) -> bool:
        """Assert permission denied for write operations. Returns True for success."""
        if authenticated and is_owner:
            return True
        with self.assert_no_db_change(db):
            if not authenticated:
                assert_not_authenticated(
                    client=client,
                    method=method,
                    url=url,
                    parameters=parameters,
                )
            else:
                assert_forbidden(
                    client=client,
                    method=method,
                    url=url,
                    detail=detail,
                    headers=headers,
                    parameters=parameters,
                )
        return False

    def assert_read_permission(  # noqa: PLR0913
        self,
        client: TestClient,
        *,
        authenticated: bool,
        is_owner: bool,
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
        if not authenticated or is_owner or public:
            return True
        assert_forbidden(
            client=client,
            method=method,
            url=url,
            detail=detail,
            headers=headers,
        )
        return False
