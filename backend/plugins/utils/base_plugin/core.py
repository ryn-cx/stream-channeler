# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from plugins.utils.base_plugin.channels import BaseChannelMixin
from plugins.utils.base_plugin.source import BaseSourceMixin

if TYPE_CHECKING:
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class BasePluginCore(BaseChannelMixin, BaseSourceMixin, ABC):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin | None = None,
        file_cache: dict[tuple[type[BaseFile[Any]], Any], BaseFile[Any]] | None = None,
    ) -> None:
        """Initialize the plugin.

        Args:
            session: The SQLAlchemy session to use for database operations.
            plugin: An optional `Plugin` instance to use instead of fetching it from the
            database.
        """
        self.session = session
        self.plugin = plugin or Plugin.get_one(session, self.plugin_name())
        """The `Plugin` record from the database."""
        self._sources = {source.key: source for source in self.plugin.sources}
        """All of the `Source` records from the database in a dict keyed by
        `Source.key`."""
        self._file_cache = file_cache if file_cache is not None else {}

    @classmethod
    def source_name(cls) -> str:
        return cls.plugin_name()

    @property
    def source(self) -> Source:
        """Return the source associated with this importer."""
        return self._sources[self.source_name()]
