# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin.file_access import BaseFileAccessMixin
from plugins.utils.base_plugin.files import BaseFile

if TYPE_CHECKING:
    from datetime import datetime


# TODO: Validate
class BaseSourceMixin(BaseFileAccessMixin, ABC):
    _sources: dict[str, Source]

    # TODO: Validate
    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    def _source_files(self) -> Sequence[BaseFile[Any]]:
        """Return the files required to upsert the source.

        The default implementation will raise because returning an empty list is more
        error-prone than explicitly raising an error."""
        raise NotImplementedError

    # TODO: Validate
    def _source_files_data_timestamp(self) -> datetime:
        return min(file.record_data_timestamp for file in self._source_files())

    def _link_to_tmdb(self) -> bool:
        """Return whether the plugin should link to TMDB."""
        return True

    def _next_source_update_at(self) -> datetime | None:
        return None

    # TODO: Validate
    def upsert_source(
        self,
        source_key: str,
        *,
        favicon_url: str | None = None,
    ) -> Source:
        """Create or update the plugin's `Source` records."""
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)

        # If there are source files use those as the data_timestamp, if there are no
        # source files set the data_timestamp to the current date.
        try:
            source_files = self._source_files()
        except NotImplementedError:
            data_timestamp = tz_datetime.now()
        else:
            self._download_if_outdated(source_files)
            data_timestamp = self._source_files_data_timestamp()
        return Source(
            key=source_key,
            favicon_url=favicon_url if favicon_url is not None else self.favicon_url(),
            link_to_tmdb=self._link_to_tmdb(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
            update_at=self._next_source_update_at(),
        ).upsert(self.plugin, existing_source)
