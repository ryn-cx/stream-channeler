# TODO: Validate
"""What the plugin, its importers and its initializer all read Roku by."""

from __future__ import annotations

from typing import override

from plugins.Roku.basic_files import BasicFiles
from plugins.Roku.constants import CONTENT_ID_REGEX
from plugins.Roku.utils import search_url

# https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae
# The title slug after the content id is decorative, only the id matters.
DETAILS_URL_REGEX = (
    rf"\/details\/(?P<details_content_key>{CONTENT_ID_REGEX})(?:\/[^\/?#]+)?(?:\/|$)"
)
# https://therokuchannel.roku.com/watch/db1607f1cff2522bb795382bb4b5bcae
WATCH_URL_REGEX = rf"\/watch\/(?P<watch_content_key>{CONTENT_ID_REGEX})(?:\/|$)"


# TODO: Validate
class RokuShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "The Roku Channel"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://therokuchannel.roku.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "therokuchannel.roku.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:  # noqa: ARG003 - Roku carries no query in a search address.
        return search_url()
