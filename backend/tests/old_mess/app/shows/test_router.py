# TODO: Validate
from app.shows.models import Show
from app.shows.schemas import (
    ShowCreate,
    ShowPublic,
    ShowUpdate,
)
from tests.old_mess.app.shows.utils import create_random_show
from tests.old_mess.app.sources.utils import create_random_source
from tests.old_mess.app.utils.base import BaseTests
from tests.old_mess.app.utils.base_create import BaseCreateTests
from tests.old_mess.app.utils.base_delete import BaseDeleteTests
from tests.old_mess.app.utils.base_get import BaseGetTests
from tests.old_mess.app.utils.base_update import BaseUpdateTests


# TODO: Validate
class ShowTestMixin(BaseTests[Show]):
    database_model = Show
    create_schema = ShowCreate
    output_schema = ShowPublic
    update_schema = ShowUpdate
    create_parent_function = staticmethod(create_random_source)
    create_record_function = staticmethod(create_random_show)


# TODO: Validate
class TestCreateShow(ShowTestMixin, BaseCreateTests[Show]):
    pass


# TODO: Validate
class TestGetShow(ShowTestMixin, BaseGetTests[Show]):
    pass


# TODO: Validate
class TestUpdateShow(ShowTestMixin, BaseUpdateTests[Show]):
    pass


# TODO: Validate
class TestDeleteShow(ShowTestMixin, BaseDeleteTests[Show]):
    pass
