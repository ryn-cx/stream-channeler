# TODO: Validate
"""Writing what a website says about a title into the rows that stand for it."""

from __future__ import annotations

from abc import ABC
from datetime import datetime

from app.models import BaseMediaMixin
from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.outdated_check import BaseOutdatedCheckMixin


# TODO: Validate
class BaseUpsertMixin(BasePluginCore, BaseOutdatedCheckMixin, ABC):
    # TODO: Validate
    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    # TODO: Validate
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        """Store the listing `title_key` names."""
        # Not an abstractmethod, because a plugin that reads a title as one of
        # several kinds writes each kind on its own and has nothing to write for
        # a title it has not been told the kind of. Such a plugin is still a
        # plugin, so what it cannot answer is raised when asked rather than kept
        # from being built at all.
        msg = f"{self.plugin_name()} does not upsert titles."
        raise NotImplementedError(msg)

    # TODO: Validate
    def upsert_source(self, source_key: str) -> Source:
        """Create or update the plugin's `Source` record(s)."""
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=self._existing_data_timestamp_or_now(existing_source),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source
