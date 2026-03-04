import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.seasons.utils import create_random_season
from tests.shows.utils import create_random_show
from tests.utils.media_router import (
    BaseCreateTests,
    BaseDeleteTests,
    BaseGetTests,
    BaseListFromParentTests,
    BaseTests,
    BaseUpdateTests,
)


class SeasonTestMixin(BaseTests):
    has_parent = True
    database_model = Season
    input_schema = SeasonPostInput
    output_model = SeasonOutput
    patch_model = SeasonPatchInput
    list_output_model = SeasonsListOutput
    endpoint_name = "seasons"
    parent_endpoint_name = "shows"
    parent_key_name = "show_id"
    model_name = "Season"
    parent_name = "Show"

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> Show:
        return create_random_show(db, user_id=user_id)

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | User | None = None,
    ) -> Season:
        if parent is not None:
            assert isinstance(parent, Show)
            return create_random_season(db, show=parent)
        return create_random_season(db, user_id=user_id)


class TestCreateSeason(SeasonTestMixin, BaseCreateTests):
    pass


class TestGetSeason(SeasonTestMixin, BaseGetTests):
    pass


class TestListSeasonsFromShow(SeasonTestMixin, BaseListFromParentTests):
    pass


class TestUpdateSeason(SeasonTestMixin, BaseUpdateTests):
    pass


class TestDeleteSeason(SeasonTestMixin, BaseDeleteTests):
    pass
