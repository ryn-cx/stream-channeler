import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.episodes.models import BaseEpisode, Episode
from app.models import BaseInputMixin
from app.seasons.models import Season


class EpisodeInput(BaseEpisode, BaseInputMixin[Episode]):
    """Input schema for creating or updating an episode."""

    def upsert(
        self,
        season: Season,
        existing_episode: Episode | None,
        protected_keys: set[str] | None = None,
    ) -> Episode:
        """Insert or update an episode in the database.

        Args:
            season: Parent season instance.
            existing_episode: Existing Episode instance to update. If NOT_PROVIDED,
                will search through season.episodes for a matching key. If None,
                will create a new episode.
            protected_keys: Keys that should not be updated if the episode already
            exists.

        Returns:
            Episode instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_episode:
            return self._update_existing_entry(existing_episode, protected_keys)

        episode = Episode.model_validate(self, update={"season_id": season.id})
        season.episodes.append(episode)
        return episode


class EpisodeOutput(BaseEpisode):
    id: uuid.UUID
    season_id: uuid.UUID


class EpisodesListOutput(BaseModel):
    data: list[EpisodeOutput]


class EpisodePostInput(BaseEpisode):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class EpisodePatchInput(BaseEpisode):
    # assignment - Patch input can ignore required values.
    key: str | None = Field(default=None)  # type: ignore[assignment]
