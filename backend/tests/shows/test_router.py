# TODO: Validate
from app.shows.models import Show
from app.shows.schemas import (
    ShowPublic,
    ShowUpdate,
    ShowCreate,
)
from tests.shows.utils import create_random_show
from tests.sources.utils import create_random_source
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_update import BaseUpdateTests


class ShowTestMixin(BaseTests[Show]):
    database_model = Show
    input_schema = ShowCreate
    output_model = ShowPublic
    patch_model = ShowUpdate
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
