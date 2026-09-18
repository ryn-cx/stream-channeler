# TODO: Validate
from __future__ import annotations

from plugins.Amazon.files import Detail, ShareLinkRedirect
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class AmazonBaseFiles(BasePlugin):
    # TODO: Validate
    def detail_file(self, link_id: str) -> Detail:
        """Return data for a title."""
        return self._cached_file(Detail, link_id)

    # TODO: Validate
    def share_link_file(self, share_id: str) -> ShareLinkRedirect:
        """Return where the share link written with `share_id` points."""
        return self._cached_file(ShareLinkRedirect, share_id)
