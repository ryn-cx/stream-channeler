# TODO: Validate
import pytest

from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
    EpisodeUpdate,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.seasons.utils import create_random_season
from tests.app.utils.base import BaseTests
from tests.app.utils.base_create import BaseCreateTests
from tests.app.utils.base_delete import BaseDeleteTests
from tests.app.utils.base_get import BaseGetTests
from tests.app.utils.base_update import BaseUpdateTests


class EpisodeTestMixin(BaseTests[Episode]):
    database_model = Episode
    create_schema = EpisodeCreate
    output_schema = EpisodeOutput
    update_schema = EpisodeUpdate
    create_parent_function = staticmethod(create_random_season)
    create_record_function = staticmethod(create_random_episode)


class TestCreateEpisode(EpisodeTestMixin, BaseCreateTests[Episode]):
    pass


class TestGetEpisode(EpisodeTestMixin, BaseGetTests[Episode]):
    @pytest.mark.skip(reason="`Episode` has no single-record GET route.")
    def test_get_permissions(self) -> None:  # type: ignore[override]
        ...

    @pytest.mark.skip(reason="`Episode` has no single-record GET route.")
    def test_get_not_found(self) -> None:  # type: ignore[override]
        ...


class TestUpdateEpisode(EpisodeTestMixin, BaseUpdateTests[Episode]):
    pass


class TestDeleteEpisode(EpisodeTestMixin, BaseDeleteTests[Episode]):
    pass
