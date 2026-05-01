# TODO: Validate
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourcePublic,
    SourceUpdate,
)
from tests.plugins.utils import create_random_plugin
from tests.sources.utils import create_random_source
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_update import BaseUpdateTests


class SourceTestMixin(BaseTests[Source]):
    database_model = Source
    create_schema = SourceCreate
    output_schema = SourcePublic
    update_schema = SourceUpdate

    create_parent_function = staticmethod(create_random_plugin)
    create_record_function = staticmethod(create_random_source)


class TestCreateSource(SourceTestMixin, BaseCreateTests[Source]):
    pass


class TestGetSource(SourceTestMixin, BaseGetTests[Source]):
    pass


class TestUpdateSource(SourceTestMixin, BaseUpdateTests[Source]):
    pass


class TestDeleteSource(SourceTestMixin, BaseDeleteTests[Source]):
    pass
