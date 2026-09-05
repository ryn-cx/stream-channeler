# TODO: Validate
"""Writing what a website says about a title into the rows that stand for it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.models import BaseMediaMixin
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.base_plugin_v2.core import BasePluginCore
from plugins.utils.base_plugin_v2.outdated_check import BaseOutdatedCheckMixin


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
    @abstractmethod
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        """Store the listing `show_key` names."""

    # TODO: Validate
    def upsert_source(self, source_key: str) -> Source:
        """Create or update the plugin's `Source` record(s)."""
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source
