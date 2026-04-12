import uuid

from sqlmodel import Field

from app.episodes.models import BaseEpisode, Episode
from app.schemas import BasePatchInputWithKey, BasePostInputWithChild
from app.seasons.models import Season


class EpisodeOutput(BaseEpisode):
    id: uuid.UUID
    season_id: uuid.UUID


class EpisodePostInput(BasePostInputWithChild[Episode, Season], BaseEpisode):
    pass


class EpisodePatchInput(BasePatchInputWithKey[Episode], BaseEpisode):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.
