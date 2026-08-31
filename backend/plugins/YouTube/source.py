# TODO: Validate


from typing import TYPE_CHECKING, override

from app.sources.models import Source
from plugins.YouTube.constants import (
    FREE_SOURCE_KEY,
    LINKS_SOURCE_KEY,
    PAID_SOURCE_KEY,
)
from plugins.YouTube.utils import HelperMixin

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
class SourceMixin(HelperMixin):
    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(), FREE_SOURCE_KEY, PAID_SOURCE_KEY, LINKS_SOURCE_KEY)

    # TODO: Validate
    @classmethod
    @override
    def _upsert_source(
        cls,
        session: Session,
        plugin: Plugin,
        source_key: str,
    ) -> Source:
        source = Source.get(session, plugin, source_key)
        return Source(
            key=source_key,
            name=source_key,
            favicon_url=cls.favicon_url(),
            data_timestamp=cls._existing_data_timestamp_or_now(source),
            plugin_id=plugin.id,
        ).upsert_and_set_update_at(plugin, source)
