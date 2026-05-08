# TODO: Validate


import dataclasses
import uuid
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.utils.route_assertions import Method

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, col, select

from app.channels.models import Channel
from app.channels.schemas import (
    ChannelCreate,
    ChannelOutput,
    ChannelUpdate,
)
from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
    EpisodeUpdate,
)
from app.models import Visibility
from app.playlists.models import Playlist
from app.playlists.schemas import (
    PlaylistCreate,
    PlaylistOutput,
    PlaylistUpdate,
)
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginOutput,
    PluginUpdate,
)
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
    SeasonUpdate,
)
from app.shows.models import Show
from app.shows.schemas import ShowCreate, ShowPublic, ShowUpdate
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourcePublic,
    SourceUpdate,
)
from app.users.models import User
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchOutput,
    WatchUpdate,
)
from tests.users.utils import (
    authentication_token_from_email,
    create_random_user,
)
from tests.utils.route_assertions import assert_forbidden, assert_not_authenticated

SUPPORTED_MODELS = (
    Channel | Episode | Season | Show | Source | Plugin | Watch | Playlist
)
PARENT_MODELS = SUPPORTED_MODELS | User

CREATE_SCHEMAS = (
    ChannelCreate
    | EpisodeCreate
    | PluginCreate
    | SeasonCreate
    | ShowCreate
    | SourceCreate
    | WatchCreate
    | PlaylistCreate
)
OUTPUT_SCHEMAS = (
    ChannelOutput
    | EpisodeOutput
    | PluginOutput
    | SeasonOutput
    | ShowPublic
    | SourcePublic
    | WatchOutput
    | PlaylistOutput
)
LIST_OUTPUT_SCHEMAS = (
    list[ChannelOutput]
    | list[EpisodeOutput]
    | list[PluginOutput]
    | list[SeasonOutput]
    | list[ShowPublic]
    | list[SourcePublic]
    | list[PlaylistOutput]
)
UPDATE_SCHEMAS = (
    ChannelUpdate
    | EpisodeUpdate
    | PluginUpdate
    | SeasonUpdate
    | ShowUpdate
    | SourceUpdate
    | WatchUpdate
    | PlaylistUpdate
)


def _pluralize(name: str) -> str:
    if name.endswith(("ch", "sh", "s", "x", "z")):
        return name + "es"
    return name + "s"


@dataclasses.dataclass
class CreatedTestData[T]:
    record: T
    user: User
    headers: dict[str, str]


class BaseTests[T: SUPPORTED_MODELS]:
    database_model: type[T]
    create_schema: type[CREATE_SCHEMAS]
    output_schema: type[OUTPUT_SCHEMAS]
    update_schema: type[UPDATE_SCHEMAS]
    create_parent_function: Callable[..., Plugin | Source | Show | Season | Episode]
    create_record_function: Callable[..., T]
    returns_list: bool = False

    def get_record_from_db(
        self,
        session_scoped_session: Session,
        record_id: uuid.UUID,
    ) -> T:
        """Get the record with the given id from the database."""
        return session_scoped_session.exec(
            select(self.database_model).where(self.database_model.id == record_id),
        ).one()

    @staticmethod
    def get_foreign_keys(model: type[SQLModel]) -> list[str]:
        return [
            field_name
            for field_name, field_info in model.model_fields.items()
            if isinstance(getattr(field_info, "foreign_key", None), str)
        ]

    @property
    def parent_key_name(self) -> str:
        keys = self.get_foreign_keys(self.database_model)
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

    def generic_record_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{record_id}"

    @contextmanager
    def assert_no_db_change(self, session_scoped_session: Session) -> Generator[None]:
        """Assert that no records were added, removed, or modified."""
        records_before = session_scoped_session.exec(select(self.database_model)).all()
        yield
        records_after = session_scoped_session.exec(select(self.database_model)).all()
        assert records_before == records_after

    def assert_other_records_unchanged(
        self,
        session_scoped_session: Session,
        updated_records: Sequence[OUTPUT_SCHEMAS],
        records_before: Sequence[T],
    ) -> None:
        """Assert only the given records changed; all others are identical."""
        updated_record_ids = [record.id for record in updated_records]
        all_records_after = session_scoped_session.exec(
            select(self.database_model),
        ).all()
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
        session_scoped_session: Session,
        new_record_ids: Sequence[uuid.UUID],
        records_before: Sequence[T],
    ) -> None:
        """Assert only the given records were added and all existing records are unchanged."""
        new_records = list(
            session_scoped_session.exec(
                select(self.database_model).where(
                    col(self.database_model.id).in_(new_record_ids),
                ),
            ).all(),
        )

        expected = sorted([*records_before, *new_records], key=lambda r: r.id)
        actual = sorted(
            session_scoped_session.exec(select(self.database_model)).all(),
            key=lambda r: r.id,
        )
        assert expected == actual

    @staticmethod
    def get_plugin(record: SUPPORTED_MODELS) -> Plugin:
        queue: list[SUPPORTED_MODELS] = [record]
        # haha BFS go brrrrr
        while queue:
            current = queue.pop()
            if isinstance(current, Plugin):
                return current
            queue.extend(
                getattr(current, key.removesuffix("_id"))
                for key in BaseTests.get_foreign_keys(type(current))
            )
        msg = f"No plugin found for {type(record).__name__}"
        raise ValueError(msg)

    def set_visibility(
        self,
        record: T,
        *,
        record_is_public: bool,
    ) -> None:
        plugin = self.get_plugin(record)
        plugin.visibility = (
            Visibility.public if record_is_public else Visibility.private
        )

    def create_test_data(
        self,
        client: TestClient,
        session: Session,
        *,
        user_is_owner: bool,
        user_is_authenticated: bool,
        record_is_public: bool,
    ) -> CreatedTestData[T]:
        """Create a user and record with the given ownership and visibility."""
        user = create_random_user(session)
        other = create_random_user(session)

        if user_is_owner:
            record = self.create_record_function(session, user.id)
        else:
            record = self.create_record_function(session, other.id)

        # Populate with random dummy data to make sure filtering works correctly.
        self.create_record_function(session, user.id)
        self.create_record_function(session, other.id)

        self.set_visibility(record, record_is_public=record_is_public)
        headers = (
            authentication_token_from_email(
                client=client,
                email=user.email,
                session=session,
            )
            if user_is_authenticated
            else {}
        )
        return CreatedTestData(record=record, user=user, headers=headers)

    def assert_cannot_access(  # noqa: PLR0913
        self,
        session: Session,
        client: TestClient,
        *,
        user_is_authenticated: bool,
        method: Method,
        url: str,
        model_name: str,
        headers: dict[str, str],
        parameters_model: SQLModel | None = None,
    ) -> None:
        parameters = (
            parameters_model.model_dump(mode="json") if parameters_model else None
        )
        with self.assert_no_db_change(session):
            if not user_is_authenticated:
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
                    detail=f"Not authorized to access this {model_name}",
                    headers=headers,
                    parameters=parameters,
                )
