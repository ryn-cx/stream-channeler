import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.episodes.utils import create_random_episode
from tests.seasons.utils import create_random_season
from tests.utils.media_router import (
    BaseCreateTests,
    BaseDeleteTests,
    BaseGetTests,
    BaseListFromParentTests,
    BaseTests,
    BaseUpdateTests,
)


class EpisodeTestMixin(BaseTests):
    has_parent = True
    database_model = Episode
    input_schema = EpisodePostInput
    output_model = EpisodeOutput
    patch_model = EpisodePatchInput
    list_output_model = EpisodesListOutput
    endpoint_name = "episodes"
    parent_endpoint_name = "seasons"
    parent_key_name = "season_id"
    model_name = "Episode"
    parent_name = "Season"

    def create_parent(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
    ) -> Season:
        return create_random_season(db, user_id=user_id)

    def create_record(
        self,
        db: Session,
        user_id: uuid.UUID | None = None,
        parent: Plugin | Source | Show | Season | User | None = None,
    ) -> Episode:
        if parent is not None:
            assert isinstance(parent, Season)
            return create_random_episode(db, season=parent)
        return create_random_episode(db, user_id=user_id)


class TestCreateEpisode(EpisodeTestMixin, BaseCreateTests):
    pass


class TestGetEpisode(EpisodeTestMixin, BaseGetTests):
    pass


class TestListEpisodesFromSeason(EpisodeTestMixin, BaseListFromParentTests):
    pass


class TestUpdateEpisode(EpisodeTestMixin, BaseUpdateTests):
    pass


class TestDeleteEpisode(EpisodeTestMixin, BaseDeleteTests):
    pass
