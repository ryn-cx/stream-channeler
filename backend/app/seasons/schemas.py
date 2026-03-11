# TODO: Validate
import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.models import BaseInputMixin
from app.seasons.models import BaseSeason, Season
from app.shows.models import Show


class SeasonInput(BaseSeason, BaseInputMixin[Season]):
    """Input schema for creating or updating a season."""

    def upsert(
        self,
        show: Show,
        existing_season: Season | None,
        protected_keys: set[str] | None = None,
    ) -> Season:
        """Insert or update a season in the database.

        Args:
            show: Parent show instance.
            existing_season: Existing Season instance to update. If NOT_PROVIDED,
                will search through show.seasons for a matching key. If None,
                will create a new season.
            protected_keys: Keys that should not be updated if the season already
            exists.

        Returns:
            Season instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_season:
            return self._update_existing_entry(existing_season, protected_keys)

        season = Season.model_validate(self, update={"show_id": show.id})
        show.seasons.append(season)
        return season


class SeasonOutput(BaseSeason):
    show_id: uuid.UUID
    id: uuid.UUID


class SeasonsListOutput(BaseModel):
    data: list[SeasonOutput]


class SeasonPostInput(BaseSeason):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SeasonPatchInput(BaseSeason):
    # assignment - Patch input can ignore required values.
    key: str | None = Field(default=None)  # type: ignore[assignment]
