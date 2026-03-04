import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
    ShowPostInput,
    ShowsListOutput,
)
from app.sources.models import Source
from app.users.models import User
from tests.shows.utils import create_random_show
from tests.sources.utils import create_random_source
from tests.utils.media_router import (
    BaseCreateTests,
    BaseDeleteTests,
    BaseGetTests,
    BaseListFromParentTests,
    BaseTests,
    BaseUpdateTests,
)


class ShowTestMixin(BaseTests):
    has_parent = True
    database_model = Show
    input_schema = ShowPostInput
    output_model = ShowOutput
    patch_model = ShowPatchInput
    list_output_model = ShowsListOutput
    endpoint_name = "shows"
    parent_endpoint_name = "sources"
    parent_key_name = "source_id"
    model_name = "Show"
    parent_name = "Source"

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> Source:
        return create_random_source(db, user_id=user_id)

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | User | None = None,
    ) -> Show:
        if parent is not None:
            assert isinstance(parent, Source)
            return create_random_show(db, source=parent)
        return create_random_show(db, user_id=user_id)


class TestCreateShow(ShowTestMixin, BaseCreateTests):
    pass


class TestGetShow(ShowTestMixin, BaseGetTests):
    pass


class TestListShowsFromSource(ShowTestMixin, BaseListFromParentTests):
    pass


class TestUpdateShow(ShowTestMixin, BaseUpdateTests):
    pass


class TestDeleteShow(ShowTestMixin, BaseDeleteTests):
    pass
