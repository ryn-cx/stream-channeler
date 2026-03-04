import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.models import BaseInputMixin
from app.plugins.models import Plugin
from app.sources.models import BaseSource, Source


class SourceInput(BaseSource, BaseInputMixin[Source]):
    """Input schema for creating or updating a source."""

    def upsert(
        self,
        plugin: Plugin,
        existing_source: Source | None,
        protected_keys: set[str] | None = None,
    ) -> Source:
        """Insert or update a source in the database.

        Args:
            plugin: Parent plugin instance.
            existing_source: Existing Source instance to update. If NOT_PROVIDED,
                will search through plugin.sources for a matching key. If None,
                will create a new source.
            protected_keys: Keys that should not be updated if the source already
            exists.

        Returns:
            Source instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_source:
            return self._update_existing_entry(existing_source, protected_keys)

        source = Source.model_validate(self, update={"plugin_id": plugin.id})
        plugin.sources.append(source)
        return source


class SourceOutput(BaseSource):
    plugin_id: uuid.UUID
    id: uuid.UUID


class SourcesListOutput(BaseModel):
    data: list[SourceOutput]
    count: int


class SourcePostInput(BaseSource):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SourcePatchInput(BaseSource):
    # assignment - Patch input can ignore required values.
    key: str | None = Field(default=None)  # type: ignore[assignment]
