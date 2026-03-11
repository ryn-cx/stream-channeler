# TODO: Validate
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
    ShowPostInput,
    ShowsListOutput,
)
from tests.shows.utils import create_random_show
from tests.sources.utils import create_random_source
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_list import BaseListFromParentTests
from tests.utils.base_update import BaseUpdateTests


class ShowTestMixin(BaseTests[Show]):
    database_model = Show
    input_schema = ShowPostInput
    output_model = ShowOutput
    patch_model = ShowPatchInput
    list_output_model = ShowsListOutput
    create_parent_function = staticmethod(create_random_source)
    create_record_function = staticmethod(create_random_show)


class TestCreateShow(ShowTestMixin, BaseCreateTests[Show]):
    pass


class TestGetShow(ShowTestMixin, BaseGetTests[Show]):
    pass


class TestListShowsFromSource(ShowTestMixin, BaseListFromParentTests[Show]):
    pass


class TestUpdateShow(ShowTestMixin, BaseUpdateTests[Show]):
    pass


class TestDeleteShow(ShowTestMixin, BaseDeleteTests[Show]):
    pass
