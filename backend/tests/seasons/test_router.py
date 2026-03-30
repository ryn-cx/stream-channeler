from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
    SeasonPostInput,
    SeasonsListOutput,
)
from tests.seasons.utils import create_random_season
from tests.shows.utils import create_random_show
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_update import BaseUpdateTests


class SeasonTestMixin(BaseTests[Season]):
    database_model = Season
    input_schema = SeasonPostInput
    output_model = SeasonOutput
    patch_model = SeasonPatchInput
    list_output_model = SeasonsListOutput

    create_parent_function = staticmethod(create_random_show)
    create_record_function = staticmethod(create_random_season)


class TestCreateSeason(SeasonTestMixin, BaseCreateTests[Season]):
    pass


class TestGetSeason(SeasonTestMixin, BaseGetTests[Season]):
    pass


class TestUpdateSeason(SeasonTestMixin, BaseUpdateTests[Season]):
    pass


class TestDeleteSeason(SeasonTestMixin, BaseDeleteTests[Season]):
    pass
