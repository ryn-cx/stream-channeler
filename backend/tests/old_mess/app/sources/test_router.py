# TODO: Validate
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourcePublic,
    SourceUpdate,
)
from tests.old_mess.app.plugins.utils import create_random_plugin
from tests.old_mess.app.sources.utils import create_random_source
from tests.old_mess.app.utils.base import BaseTests
from tests.old_mess.app.utils.base_create import BaseCreateTests
from tests.old_mess.app.utils.base_delete import BaseDeleteTests
from tests.old_mess.app.utils.base_get import BaseGetTests
from tests.old_mess.app.utils.base_update import BaseUpdateTests


# TODO: Validate
class SourceTestMixin(BaseTests[Source]):
    database_model = Source
    create_schema = SourceCreate
    output_schema = SourcePublic
    update_schema = SourceUpdate

    create_parent_function = staticmethod(create_random_plugin)
    create_record_function = staticmethod(create_random_source)


# TODO: Validate
class TestCreateSource(SourceTestMixin, BaseCreateTests[Source]):
    pass


# TODO: Validate
class TestGetSource(SourceTestMixin, BaseGetTests[Source]):
    pass


# TODO: Validate
class TestUpdateSource(SourceTestMixin, BaseUpdateTests[Source]):
    pass


# TODO: Validate
class TestDeleteSource(SourceTestMixin, BaseDeleteTests[Source]):
    pass
