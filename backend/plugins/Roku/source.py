# TODO: Validate
"""The source the plugin's titles belong to."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.sources.models import Source
from plugins.Roku.utils import HelperMixin

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
class SourceMixin(HelperMixin):
    """The plugin's own source."""

    # TODO: Validate
    @classmethod
    @override
    def _upsert_source(
        cls,
        session: Session,
        plugin: Plugin,
        source_key: str,
    ) -> Source:
        source = Source.get_from_memory(session, plugin, source_key)
        return Source(
            key=source_key,
            name=cls.plugin_name(),
            favicon_url=cls.favicon_url(),
            plugin_id=plugin.id,
        ).upsert_and_set_update_at(plugin, source)
