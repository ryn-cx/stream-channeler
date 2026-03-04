import uuid

from pydantic import BaseModel
from sqlmodel import Field, Session

from app.models import BaseInputMixin
from app.plugins.models import BaseFile, BasePlugin, File, Plugin
from app.users.models import User


class PluginInput(BasePlugin, BaseInputMixin[Plugin]):
    """Input schema for creating or updating a plugin."""

    user_id: uuid.UUID | None = None

    def upsert(
        self,
        db_or_user: User | Session,
        existing_plugin: Plugin | None,
        protected_keys: set[str] | None = None,
    ) -> Plugin:
        """Insert or update a plugin in the database.

        Args:
            parent: User who owns the plugin, or a Session for system plugins.
            existing_plugin: Existing Plugin instance to update. If None,
                will create a new plugin.
            protected_keys: Keys that should not be updated if the plugin already
            exists.

        Returns:
            Plugin instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_plugin:
            return self._update_existing_entry(existing_plugin, protected_keys)

        if isinstance(db_or_user, User):
            plugin = Plugin.model_validate(self, update={"user_id": db_or_user.id})
            db_or_user.plugins.append(plugin)
        else:
            plugin = Plugin.model_validate(self)
            db_or_user.add(plugin)
        return plugin


class FileInput(BaseFile, BaseInputMixin[File]):
    """Input schema for creating or updating a file."""

    def upsert(
        self,
        plugin: Plugin,
        existing_file: File | None,
        protected_keys: set[str] | None = None,
    ) -> File:
        """Insert or update a file in the database.

        Args:
            db: Database session.
            plugin: Parent plugin instance.
            existing_file: Existing File instance to update. If NOT_PROVIDED,
                will look up the file from the database using the key. If None,
                will create a new file.
            protected_keys: Keys that should not be updated if the file already
            exists.

        Returns:
            File instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_file:
            return self._update_existing_entry(existing_file, protected_keys)

        file = File.model_validate(self, update={"plugin_id": plugin.id})
        plugin.files.append(file)
        return file


class PluginOutput(BasePlugin):
    id: uuid.UUID
    user_id: uuid.UUID | None = None


class PluginsListOutput(BaseModel):
    data: list[PluginOutput]
    count: int


class PluginPostInput(BasePlugin):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class PluginPatchInput(BasePlugin):
    # assignment - Patch input can ignore required values.
    key: str | None = Field(default=None)  # type: ignore[assignment]
