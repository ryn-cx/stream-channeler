# TODO: Validate


from functools import partial
from typing import override

from app.sources.models import Source
from plugins.YouTube.helpers import (
    FREE_SOURCE_KEY,
    PAID_SOURCE_KEY,
    HelperMixin,
)


# TODO: Validate
class SourceMixin(HelperMixin, register=False):
    @override
    def initialize_sources(self) -> None:
        for source_key in (
            self.plugin_key(),
            FREE_SOURCE_KEY,
            PAID_SOURCE_KEY,
        ):
            self._initialize_source(
                source_key,
                partial(self._upsert_source, source_key),
            )

    @override
    def _upsert_source(self, source_key: str) -> Source:
        source = Source.get(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=source_key,
            favicon_url=self.FAVICON_URL,
            data_timestamp=self._existing_data_timestamp_or_now(source),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)
