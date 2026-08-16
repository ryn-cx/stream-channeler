# TODO: Validate
"""The source every Netflix title belongs to."""

from __future__ import annotations

from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Netflix.helpers import HelperMixin


# TODO: Validate
class SourceMixin(HelperMixin, register=False):
    """The plugin's own source."""

    # TODO: Validate
    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            data_timestamp=tz_datetime.now(),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)
