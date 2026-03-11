# TODO: Validate
import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.models import BaseInputMixin
from app.shows.models import BaseShow, Show
from app.sources.models import Source


class ShowInput(BaseShow, BaseInputMixin[Show]):
    """Input schema for creating or updating a show."""

    def upsert(
        self,
        source: Source,
        existing_show: Show | None,
        protected_keys: set[str] | None = None,
    ) -> Show:
        """Insert or update a show in the database.

        Args:
            source: Parent source instance.
            existing_show: Existing Show instance to update. If NOT_PROVIDED,
                will search through source.shows for a matching key. If None,
                will create a new show.
            protected_keys: Keys that should not be updated if the show already
            exists.

        Returns:
            Show instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_show:
            return self._update_existing_entry(existing_show, protected_keys)

        show = Show.model_validate(self, update={"source_id": source.id})
        source.shows.append(show)
        return show


class ShowOutput(BaseShow):
    source_id: uuid.UUID
    id: uuid.UUID


class ShowsListOutput(BaseModel):
    data: list[ShowOutput]


class ShowPostInput(BaseShow):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class ShowPatchInput(BaseShow):
    # assignment - Patch input can ignore required values.
    key: str | None = Field(default=None)  # type: ignore[assignment]
