# TODO: Validate
from __future__ import annotations

from plugins.Amazon.files import Detail, ShareLinkRedirect
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class AmazonBaseFiles(BasePlugin):
    # TODO: Validate
    def detail_file(self, title_key: str) -> Detail:
        """Return data for a title."""
        return self._cached_file(Detail, title_key)

    # TODO: Validate
    def share_link_file(self, share_key: str) -> ShareLinkRedirect:
        """Return where the share link written with `share_key` points."""
        return self._cached_file(ShareLinkRedirect, share_key)
