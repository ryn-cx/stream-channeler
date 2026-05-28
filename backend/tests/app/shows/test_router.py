# TODO: Validate
from app.shows.models import Show
from app.shows.schemas import (
    ShowCreate,
    ShowPublic,
    ShowUpdate,
)
from tests.app.shows.utils import create_random_show
from tests.app.sources.utils import create_random_source
from tests.app.utils.base import BaseTests
from tests.app.utils.base_create import BaseCreateTests
from tests.app.utils.base_delete import BaseDeleteTests
from tests.app.utils.base_get import BaseGetTests
from tests.app.utils.base_update import BaseUpdateTests


class ShowTestMixin(BaseTests[Show]):
    database_model = Show
    create_schema = ShowCreate
    output_schema = ShowPublic
    update_schema = ShowUpdate
    create_parent_function = staticmethod(create_random_source)
    create_record_function = staticmethod(create_random_show)


class TestCreateShow(ShowTestMixin, BaseCreateTests[Show]):
    pass


class TestGetShow(ShowTestMixin, BaseGetTests[Show]):
    pass


class TestUpdateShow(ShowTestMixin, BaseUpdateTests[Show]):
    pass


class TestDeleteShow(ShowTestMixin, BaseDeleteTests[Show]):
    pass
