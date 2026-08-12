# TODO: Validate
import uuid
from typing import override

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.schemas import PluginOutput
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchesListOutput,
    WatchItem,
    WatchOutput,
    WatchUpdate,
)
from tests.old_mess.app.episodes.utils import create_random_episode
from tests.old_mess.app.users.utils import create_random_user
from tests.old_mess.app.utils.base import BaseTests
from tests.old_mess.app.utils.base_create import BaseCreateTests
from tests.old_mess.app.utils.base_delete import BaseDeleteTests
from tests.old_mess.app.utils.base_get import UserOwnedGetMixin
from tests.old_mess.app.utils.base_update import BaseUpdateTests
from tests.old_mess.app.utils.route_assertions import (
    assert_conflict,
    assert_success,
    assert_success_list,
)
from tests.old_mess.app.utils.utils import dump_random_model
from tests.old_mess.app.watches.utils import create_random_watch


# TODO: Validate
class WatchTestMixin(BaseTests[Watch]):
    database_model = Watch
    create_schema = WatchCreate
    output_schema = WatchOutput
    update_schema = WatchUpdate
    create_parent_function = staticmethod(create_random_episode)
    create_record_function = staticmethod(create_random_watch)
    returns_list = True
    # This model is too different from the base tests, actually adding it to the
    # list_output_model types would just break all of the existing tests.
    real_list_output_model = WatchesListOutput

    # Watch has multiple foreign keys so this value needs to be manually specified as
    # episode_id because it connects to plugin which is responsible for the permissions.
    # TODO: Validate
    @property
    def parent_key_name(self) -> str:
        return "episode_id"


# There is somehow no overlap with UserOwnedCreateMixin so it is intentionally not used
# for this class.
# TODO: Validate
class TestCreateWatch(WatchTestMixin, BaseCreateTests[Watch]):
    # TODO: Validate
    def create_record_url(self, parent_id: uuid.UUID | str | None = None) -> str:
        return f"{settings.API_V1_STR}/episodes/{parent_id}/watches"

    # The user does not need to own a plugin to create watches for it if the plugin is
    # public.
    # TODO: Validate
    def can_create_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> bool:
        if not user_is_authenticated:
            return False
        if user_is_owner or record_is_public:
            return True
        return user_is_superuser

    # Watches have different properties if unverified siblings exist that are tested
    # independently.
    # TODO: Validate
    @pytest.mark.skip
    def test_create_with_existing_records(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        existing_record_count: int,
    ) -> None:
        pass

    # TODO: Validate
    @pytest.mark.parametrize("sibling_count", [1, 2])
    def test_create_watch_creates_siblings(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        sibling_count: int,
    ) -> None:
        """Test that creating a watch only writes a row for the chosen episode."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        # Get values then delete existing watch so multiple will be created at once.
        plugin = initial_test_data.record.episode.season.show.source.plugin
        key = initial_test_data.record.episode.key
        canonical_episode_id = initial_test_data.record.episode.canonical_episode_id
        session_scoped_session.delete(initial_test_data.record)

        sibling_episodes = [
            create_random_episode(
                session_scoped_session,
                plugin,
                key=key,
                canonical_episode_id=canonical_episode_id,
            )
            for _ in range(sibling_count)
        ]

        assert_success_list(
            client=session_scoped_client,
            method="post",
            url=self.create_record_url(initial_test_data.record.episode.id),
            output_schema=WatchOutput,
            headers=initial_test_data.headers,
            parameters=dump_random_model(WatchCreate),
        )

        watches = session_scoped_session.exec(
            select(Watch)
            .join(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .where(
                Watch.user_id == initial_test_data.user.id,
                Episode.key == key,
                Source.plugin_id == plugin.id,
            ),
        ).all()
        # The watch links to one episode; the siblings sharing its
        # the canonical episode are resolved when the watches are read instead.
        watched_episode_ids = {watch.episode_id for watch in watches}
        assert len(watches) == 1
        assert watched_episode_ids == {initial_test_data.record.episode.id}
        for episode in sibling_episodes:
            assert episode.id not in watched_episode_ids

    # TODO: Validate
    def test_create_watch_rejects_when_unverified_exists(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Test that creating a watch fails if an unverified watch exists."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        initial_test_data.record.verified = False

        with self.assert_no_db_change(session_scoped_session):
            assert_conflict(
                client=session_scoped_client,
                method="post",
                url=self.create_record_url(initial_test_data.record.episode.id),
                detail="Episode already has an unverified watch. Verify or delete it first.",
                headers=initial_test_data.headers,
                parameters=dump_random_model(WatchCreate),
            )

    # TODO: Validate
    def test_create_watch_rejects_when_sibling_has_unverified(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Test that creating a watch fails if a sibling has an unverified watch."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        initial_test_data.record.verified = False

        sibling_episode = create_random_episode(
            session_scoped_session,
            initial_test_data.record.episode.season.show.source.plugin,
            key=initial_test_data.record.episode.key,
            canonical_episode_id=initial_test_data.record.episode.canonical_episode_id,
        )

        with self.assert_no_db_change(session_scoped_session):
            assert_conflict(
                client=session_scoped_client,
                method="post",
                url=self.create_record_url(sibling_episode.id),
                detail="Episode already has an unverified watch. Verify or delete it first.",
                headers=initial_test_data.headers,
                parameters=dump_random_model(WatchCreate),
            )

    # TODO: Validate
    def test_create_watch_allowed_after_verification(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Test that creating a watch succeeds after the existing one is verified."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        initial_test_data.record.verified = True

        assert_success_list(
            client=session_scoped_client,
            method="post",
            url=self.create_record_url(initial_test_data.record.episode.id),
            output_schema=WatchOutput,
            headers=initial_test_data.headers,
            parameters=dump_random_model(WatchCreate),
        )


# Pretty much completely rewritten from BaseGetTests because the verification is more
# complex.
# TODO: Validate
class TestGetWatch(WatchTestMixin, UserOwnedGetMixin[Watch]):
    # TODO: Validate
    @pytest.mark.skip(reason="`Watch` has no single-record GET route.")
    def test_get_permissions(self) -> None:  # type: ignore[override]
        ...

    # TODO: Validate
    @pytest.mark.skip(reason="`Watch` has no single-record GET route.")
    def test_get_not_found(self) -> None:  # type: ignore[override]
        ...

    # TODO: Validate
    def get_record_list_url(
        self,
        parent_id: uuid.UUID | str | None = None,  # noqa: ARG002
    ) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}"

    # TODO: Validate
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
            expected.shows[show.id] = ShowPublic.model_validate(show)
            expected.sources[source.id] = SourcePublic.model_validate(source)
            expected.plugins[plugin.id] = PluginOutput.model_validate(plugin)
        return expected

    # TODO: Validate
    @staticmethod
    def assert_watches(
        output: WatchesListOutput,
        expected: WatchesListOutput,
    ) -> None:
        # Make sure the watches are correct
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

    # Watches need completely different verification style due to the data structure
    # being completely different since they include season/show/source/plugin data.
    # TODO: Validate
    @override
    def assert_api_get_list_success(
        self,
        client: TestClient,
        session: Session,
        parent_id: uuid.UUID,
        headers: dict[str, str],
        expected_count: int = 1,
    ) -> None:
        output = assert_success(
            client,
            "get",
            self.get_record_list_url(),
            WatchesListOutput,
            headers,
        )
        watch_ids = [watch.id for watch in output.watches]
        all_watches = session.exec(
            select(Watch).where(col(Watch.id).in_(watch_ids)),  # type: ignore[union-attr]
        ).all()
        expected = self.build_expected(*all_watches)
        self.assert_watches(output, expected)

    # TODO: Validate
    def can_get_record(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,  # noqa: ARG002
        user_is_superuser: bool,
    ) -> bool:
        if not user_is_authenticated:
            return False
        if user_is_owner:
            return True
        return user_is_superuser

    # TODO: Validate
    def test_list_excludes_other_users_watches(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Other users' watches for the same episode should not appear."""
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        episode = initial_test_data.record.episode
        other_user = create_random_user(session_scoped_session)
        create_random_watch(session_scoped_session, episode, watch_user=other_user)

        # This works because the number of expected results will be 1 so if both user's
        # watches are returned then the test will fail.
        self.assert_api_get_list_success(
            session_scoped_client,
            session_scoped_session,
            initial_test_data.user.id,
            initial_test_data.headers,
        )


# TODO: Validate
class TestUpdateWatch(WatchTestMixin, BaseUpdateTests[Watch]):
    pass


# TODO: Validate
class TestDeleteWatch(WatchTestMixin, BaseDeleteTests[Watch]):
    pass


# TODO: Validate
class TestSyncWatches:
    """Syncing should create watches for sibling episodes that are missing them."""
