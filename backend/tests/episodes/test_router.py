# TODO: Validate
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
)
from tests.episodes.utils import create_random_episode
from tests.seasons.utils import create_random_season
from tests.utils.base import BaseTests
from tests.utils.base_create import BaseCreateTests
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import BaseGetTests
from tests.utils.base_update import BaseUpdateTests


class EpisodeTestMixin(BaseTests[Episode]):
    database_model = Episode
    input_schema = EpisodePostInput
    output_model = EpisodeOutput
    patch_model = EpisodePatchInput
    create_parent_function = staticmethod(create_random_season)
    create_record_function = staticmethod(create_random_episode)


class TestCreateEpisode(EpisodeTestMixin, BaseCreateTests[Episode]):
    pass


class TestGetEpisode(EpisodeTestMixin, BaseGetTests[Episode]):
    pass


class TestUpdateEpisode(EpisodeTestMixin, BaseUpdateTests[Episode]):
    pass


class TestDeleteEpisode(EpisodeTestMixin, BaseDeleteTests[Episode]):
    pass
