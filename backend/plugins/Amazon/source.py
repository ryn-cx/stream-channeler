# TODO: Validate
"""The sources a title belongs to, by how it can be watched."""

from __future__ import annotations

from app.sources.models import Source
from plugins.Amazon.constants import PURCHASE_SOURCE_SUFFIX
from plugins.Amazon.files import FileMixin
from plugins.Amazon.utils import UtilsMixin


# TODO: Validate
class SourceMixin(UtilsMixin, FileMixin):
    """The plugin's own source and the one it keeps each channel's titles in."""

    # TODO: Validate
    def title_sources(self, show_key: str) -> list[Source]:
        """Return every `Source` a title belongs to, by how it can be watched.

        A title is often offered more than one way, such as with a channel
        subscription and as a purchase, and each way is a source of its own so
        the title is found however the user can watch it. Only a title included
        with Prime belongs to Prime Video itself.
        """
        detail_file = self.detail_file(show_key)
        sources = [
            self._extra_source(
                f"{self.plugin_name()}:{channel.benefit_id}",
                f"{self.plugin_name()} ({channel.name})",
            )
            for channel in detail_file.channels()
        ]
        if detail_file.included_with_prime():
            sources.append(self.source)
        if detail_file.purchasable():
            sources.append(
                self._extra_source(
                    f"{self.plugin_name()}:{PURCHASE_SOURCE_SUFFIX}",
                    f"{self.plugin_name()} ({PURCHASE_SOURCE_SUFFIX})",
                ),
            )
        # A title with no way to watch it listed still belongs somewhere.
        return sources or [self.source]

    # TODO: Validate
    def _extra_source(self, source_key: str, name: str) -> Source:
        """Return one of the plugin's `Source`s other than its default one."""
        # Looked up against the database rather than only the session, since a
        # source other than the default is made the first time a title needs it
        # and nothing loads it back into a later session before this reads it.
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=name,
            favicon_url=self.favicon_url(),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source
