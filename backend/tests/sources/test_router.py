from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
    SourcePostInput,
    SourcesListOutput,
)
from tests.plugins.utils import create_random_plugin
from tests.sources.utils import create_random_source
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_list import BaseListFromParentTests
from tests.utils.base_update import BaseUpdateTests


class SourceTestMixin(BaseTests[Source]):
    database_model = Source
    input_schema = SourcePostInput
    output_model = SourceOutput
    patch_model = SourcePatchInput
    list_output_model = SourcesListOutput

    create_parent_function = staticmethod(create_random_plugin)
    create_record_function = staticmethod(create_random_source)


class TestCreateSource(SourceTestMixin, BaseCreateTests[Source]):
    pass


class TestGetSource(SourceTestMixin, BaseGetTests[Source]):
    pass


class TestListSourcesFromPlugin(SourceTestMixin, BaseListFromParentTests[Source]):
    pass


class TestUpdateSource(SourceTestMixin, BaseUpdateTests[Source]):
    pass


class TestDeleteSource(SourceTestMixin, BaseDeleteTests[Source]):
    pass
