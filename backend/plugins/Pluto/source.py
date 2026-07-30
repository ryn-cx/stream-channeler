# TODO: Validate
from __future__ import annotations

from app.sources.models import Source
from plugins.Pluto.helpers import HelperMixin

# The website serves every on-demand page under a locale segment.


class SourceMixin(HelperMixin, register=False):
    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.FAVICON_URL,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)
