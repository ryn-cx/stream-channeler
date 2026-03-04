import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from app.users.models import User
from tests.old_tests.utils.media import (
    create_random_plugin,
    create_random_source,
)
from tests.utils.media_router import (
    BaseCreateTests,
    BaseDeleteTests,
    BaseGetTests,
    BaseListFromParentTests,
    BaseTests,
    BaseUpdateTests,
)


class SourceTestMixin(BaseTests):
    has_parent = True
    database_model = Source
    input_schema = SourcePostInput
    output_model = SourceOutput
    patch_model = SourcePatchInput
    list_output_model = SourcesListOutput
    endpoint_name = "sources"
    parent_endpoint_name = "plugins"
    parent_key_name = "plugin_id"
    model_name = "Source"
    parent_name = "Plugin"

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> Plugin:
        return create_random_plugin(db, user_id=user_id)

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | User | None = None,
    ) -> Source:
        if parent is not None:
            assert isinstance(parent, Plugin)
            return create_random_source(db, plugin=parent)
        return create_random_source(db, user_id=user_id)


class TestCreateSource(SourceTestMixin, BaseCreateTests):
    pass


class TestGetSource(SourceTestMixin, BaseGetTests):
    pass


class TestListSourcesFromPlugin(SourceTestMixin, BaseListFromParentTests):
    pass


class TestUpdateSource(SourceTestMixin, BaseUpdateTests):
    pass


class TestDeleteSource(SourceTestMixin, BaseDeleteTests):
    pass
