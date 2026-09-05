# TODO: Validate


from typing import override

from app.sources.models import Source
from plugins.YouTube.constants import (
    FREE_SOURCE_KEY,
    LINKS_SOURCE_KEY,
    PAID_SOURCE_KEY,
)
from plugins.YouTube.utils import UtilsMixin


# TODO: Validate
class SourceMixin(UtilsMixin):
    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(), FREE_SOURCE_KEY, PAID_SOURCE_KEY, LINKS_SOURCE_KEY)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            data_timestamp=self._existing_data_timestamp_or_now(existing_source),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source
