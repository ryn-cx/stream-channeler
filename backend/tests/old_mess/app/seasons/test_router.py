# TODO: Validate


from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
    SeasonUpdate,
)
from tests.old_mess.app.seasons.utils import create_random_season
from tests.old_mess.app.shows.utils import create_random_show
from tests.old_mess.app.utils.base import BaseTests
from tests.old_mess.app.utils.base_create import BaseCreateTests
from tests.old_mess.app.utils.base_delete import BaseDeleteTests
from tests.old_mess.app.utils.base_get import BaseGetTests
from tests.old_mess.app.utils.base_update import BaseUpdateTests


# TODO: Validate
class SeasonTestMixin(BaseTests[Season]):
    database_model = Season
    create_schema = SeasonCreate
    output_schema = SeasonOutput
    update_schema = SeasonUpdate

    create_parent_function = staticmethod(create_random_show)
    create_record_function = staticmethod(create_random_season)


# TODO: Validate
class TestCreateSeason(SeasonTestMixin, BaseCreateTests[Season]):
    pass


# TODO: Validate
class TestGetSeason(SeasonTestMixin, BaseGetTests[Season]):
    pass


# TODO: Validate
class TestUpdateSeason(SeasonTestMixin, BaseUpdateTests[Season]):
    pass


# TODO: Validate
class TestDeleteSeason(SeasonTestMixin, BaseDeleteTests[Season]):
    pass
