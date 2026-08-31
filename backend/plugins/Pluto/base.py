# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Pluto.source import SourceMixin
from plugins.Pluto.upsert import UpsertMixin


# TODO: Validate
class PlutoBase(UpsertMixin, SourceMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Pluto TV"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://pluto.tv/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "pluto.tv"
