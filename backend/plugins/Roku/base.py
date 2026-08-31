# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Roku.source import SourceMixin
from plugins.Roku.upsert import UpsertMixin


# TODO: Validate
class RokuBase(UpsertMixin, SourceMixin):
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
