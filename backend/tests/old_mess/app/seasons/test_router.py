# TODO: Validate
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.seasons.models import Season
from app.media.identifiers import tmdb_identifier
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
    SeasonUpdate,
)
from tests.old_mess.app.seasons.utils import create_random_season
from tests.old_mess.app.shows.utils import create_random_show
from tests.old_mess.app.utils.base import BaseTests
from tests.old_mess.app.utils.base_create import BaseCreateTests
from tests.old_mess.app.utils.base_delete import BaseDeleteTests
from tests.old_mess.app.utils.base_get import BaseGetTests
from tests.old_mess.app.utils.base_update import BaseUpdateTests
from tests.old_mess.app.utils.route_assertions import assert_success


# TODO: Validate
class SeasonTestMixin(BaseTests[Season]):
    database_model = Season
    create_schema = SeasonCreate
    output_schema = SeasonOutput
    update_schema = SeasonUpdate

    create_parent_function = staticmethod(create_random_show)
    create_record_function = staticmethod(create_random_season)


# TODO: Validate
class TestCreateSeason(SeasonTestMixin, BaseCreateTests[Season]):
    pass


# TODO: Validate
class TestGetSeason(SeasonTestMixin, BaseGetTests[Season]):
    pass


# TODO: Validate
class TestUpdateSeason(SeasonTestMixin, BaseUpdateTests[Season]):
    pass


# TODO: Validate
class TestDeleteSeason(SeasonTestMixin, BaseDeleteTests[Season]):
    pass


# TODO: Validate
class TestUpdateSeasonRemerge(SeasonTestMixin):
    # TODO: Validate
    def patch_tmdb_id(
        self,
        session: Session,
        client: TestClient,
        original_tmdb_id: int,
        new_tmdb_id: int,
    ) -> int:
        """Patch a `Season` onto `new_tmdb_id` and count the relinks it caused.

        The TMDB id lives in the `season_identifier` now, so the patch names the
        identifier and the id is what the `Season` reads back off it.
        """
        setup = self.create_test_data(
            client=client,
            session=session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        setup.record.season_identifier = tmdb_identifier("tv", original_tmdb_id)
        session.commit()

        with patch("app.seasons.router.relink_season_children") as relink:
            assert_success(
                client=client,
                method="patch",
                url=self.generic_record_url(setup.record.id),
                output_schema=SeasonOutput,
                headers=setup.headers,
                parameters={
                    "season_identifier": tmdb_identifier("tv", new_tmdb_id),
                },
            )
        return relink.call_count

    # TODO: Validate
    def test_changed_tmdb_id_relinks_episodes(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Ensure a new TMDB season reruns the children through TMDB."""
        call_count = self.patch_tmdb_id(
            session_scoped_session,
            session_scoped_client,
            original_tmdb_id=100,
            new_tmdb_id=200,
        )
        assert call_count == 1

    # TODO: Validate
    def test_unchanged_tmdb_id_does_not_relink_episodes(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """Ensure an unchanged `tmdb_id` leaves the children alone."""
        call_count = self.patch_tmdb_id(
            session_scoped_session,
            session_scoped_client,
            original_tmdb_id=100,
            new_tmdb_id=100,
        )
        assert call_count == 0
