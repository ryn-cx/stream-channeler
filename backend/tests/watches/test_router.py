# TODO: Validate
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.episodes.schemas import EpisodeOutput
from app.plugins.schemas import PluginOutput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowOutput
from app.sources.schemas import SourceOutput
from app.utils import tz_datetime
from app.watches.models import Watch
from app.watches.schemas import (
    WatchesListOutput,
    WatchItem,
    WatchOutput,
    WatchPatchInput,
    WatchPostInput,
)
from tests.episodes.utils import create_random_episode
from tests.users.utils import CreatedUser, create_random_user_alt
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_update import BaseUpdateTests
from tests.utils.route_assertions import (
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
    assert_success,
)
from tests.utils.utils import build_random_model, dump_random_model
from tests.watches.utils import create_random_watch

WATCHES_URL = f"{settings.API_V1_STR}/watches"


class WatchTestMixin(BaseTests[Watch]):
    database_model = Watch
    input_schema = WatchPostInput
    output_model = WatchOutput
    patch_model = WatchPatchInput
    create_parent_function = staticmethod(create_random_episode)
    create_record_function = staticmethod(create_random_watch)

    def setup_watch_visibility(
        self,
        client: TestClient,
        db: Session,
        *,
        is_owner: bool,
        public: bool,
    ) -> tuple[Watch, CreatedUser]:
        """Create a watch and configure plugin visibility directly."""
        user = create_random_user_alt(client, db)
        watch = create_random_watch(db, user_id=user.id)
        plugin = watch.episode.season.show.source.plugin
        if is_owner:
            plugin.user_id = user.id
        else:
            plugin.user_id = create_random_user_alt(client, db).id
        plugin.public = public
        db.flush()
        return watch, user


class TestCreateWatch(WatchTestMixin, BaseCreateTests[Watch]):
    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("is_owner", [True, False])
    def test_create_permissions(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        is_owner: bool,
        public: bool,
    ) -> None:
        """Watches can be created on public plugins by non-owners."""
        authenticated = user_type != "anonymous"
        watch, user = self.setup_watch_visibility(
            client,
            db,
            is_owner=is_owner,
            public=public,
        )
        episode = watch.episode
        headers = user.headers if authenticated else {}
        parameters = dump_random_model(self.input_schema)

        if not authenticated:
            with self.assert_no_db_change(db):
                assert_not_authenticated(
                    client=client,
                    method="post",
                    url=self.create_url(episode.id),
                    parameters=parameters,
                )
        elif is_owner or public:
            self.assert_create_success(
                client,
                db,
                episode.id,
                headers,
                build_random_model(self.input_schema),
            )
        else:
            with self.assert_no_db_change(db):
                assert_forbidden(
                    client=client,
                    method="post",
                    url=self.create_url(episode.id),
                    detail=f"Not authorized to access this {self.parent_name}",
                    headers=headers,
                    parameters=parameters,
                )

    def test_create_defaults(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        """Minimal create should set verified=False and watch_date to now."""
        watch, user = self.setup_watch_visibility(
            client,
            db,
            is_owner=True,
            public=False,
        )
        episode = watch.episode
        parameters = dump_random_model(WatchPostInput, "minimal")
        before = tz_datetime.now()
        data = assert_success(
            client=client,
            method="post",
            url=self.create_url(episode.id),
            output_model=WatchOutput,
            headers=user.headers,
            parameters=parameters,
        )
        after = tz_datetime.now()

        assert data.verified is False
        assert before <= data.watch_date.astimezone(before.tzinfo) <= after
        self.assert_saved_to_db(db, data.id, data)


# Watches intentionally do not filter by ownership or public status.
class TestGetWatch(WatchTestMixin):
    """Watch GET always requires auth and ownership."""

    def test_get_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=self.entry_url(str(uuid.uuid4())),
            detail="Watch not found",
            headers=user.headers,
        )

    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    @pytest.mark.parametrize("is_owner", [True, False])
    def test_get_visibility(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        is_owner: bool,
    ) -> None:
        authenticated = user_type != "anonymous"
        user = create_random_user_alt(client, db)
        if is_owner:
            watch = create_random_watch(db, user_id=user.id)
        else:
            other = create_random_user_alt(client, db)
            watch = create_random_watch(db, user_id=other.id)

        if not authenticated:
            assert_not_authenticated(
                client=client,
                method="get",
                url=self.entry_url(watch.id),
            )
        elif is_owner:
            content = assert_success(
                client=client,
                method="get",
                url=self.entry_url(watch.id),
                output_model=WatchOutput,
                headers=user.headers,
            )
            assert WatchOutput.model_validate(watch) == content
        else:
            assert_forbidden(
                client=client,
                method="get",
                url=self.entry_url(watch.id),
                detail="Not authorized to access this Watch",
                headers=user.headers,
            )


class TestUpdateWatch(WatchTestMixin, BaseUpdateTests[Watch]):
    pass


class TestDeleteWatch(WatchTestMixin, BaseDeleteTests[Watch]):
    pass


class TestListWatches(WatchTestMixin):
    @staticmethod
    def build_expected(*watches: Watch) -> WatchesListOutput:
        expected = WatchesListOutput(
            watches=[],
            episodes={},
            seasons={},
            shows={},
            sources={},
            plugins={},
        )
        for watch in watches:
            episode = watch.episode
            season = episode.season
            show = season.show
            source = show.source
            plugin = source.plugin

            expected.watches.append(WatchItem.model_validate(watch))
            expected.episodes[episode.id] = EpisodeOutput.model_validate(episode)
            expected.seasons[season.id] = SeasonOutput.model_validate(season)
            expected.shows[show.id] = ShowOutput.model_validate(show)
            expected.sources[source.id] = SourceOutput.model_validate(source)
            expected.plugins[plugin.id] = PluginOutput.model_validate(plugin)
        return expected

    @staticmethod
    def assert_watches(
        output: WatchesListOutput,
        expected: WatchesListOutput,
    ) -> None:
        output.watches.sort(key=lambda w: w.id)
        expected.watches.sort(key=lambda w: w.id)
        assert output == expected

        # Make sure there were no duplicates records in the output.
        assert len(output.watches) == len(set(output.watches))
        assert len(output.episodes) == len(set(output.episodes))
        assert len(output.seasons) == len(set(output.seasons))
        assert len(output.shows) == len(set(output.shows))
        assert len(output.sources) == len(set(output.sources))
        assert len(output.plugins) == len(set(output.plugins))

    @pytest.mark.parametrize("public", [True, False])
    @pytest.mark.parametrize("user_type", ["logged_in", "anonymous"])
    def test_list(
        self,
        client: TestClient,
        db: Session,
        *,
        user_type: str,
        public: bool,
    ) -> None:
        authenticated = user_type != "anonymous"
        watch, user = self.setup_watch_visibility(
            client,
            db,
            is_owner=True,
            public=public,
        )

        if not authenticated:
            assert_not_authenticated(client=client, method="get", url=WATCHES_URL)
        else:
            expected = self.build_expected(watch)
            output = assert_success(
                client=client,
                method="get",
                url=WATCHES_URL,
                output_model=WatchesListOutput,
                headers=user.headers,
            )
            self.assert_watches(output, expected)

    @pytest.mark.parametrize("watch_count", [0, 1, 2])
    def test_list_data(
        self,
        client: TestClient,
        db: Session,
        *,
        watch_count: int,
    ) -> None:
        user = create_random_user_alt(client, db)
        watches: list[Watch] = []
        for _ in range(watch_count):
            watch = create_random_watch(db, user_id=user.id)
            watches.append(watch)

        # Other user's watches should not appear in results.
        other_user = create_random_user_alt(client, db)
        create_random_watch(db, user_id=other_user.id)

        expected = self.build_expected(*watches)
        output = assert_success(
            client=client,
            method="get",
            url=WATCHES_URL,
            output_model=WatchesListOutput,
            headers=user.headers,
        )
        self.assert_watches(output, expected)
