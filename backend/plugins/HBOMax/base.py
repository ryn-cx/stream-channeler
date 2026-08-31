# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.HBOMax.source import SourceMixin
from plugins.HBOMax.upsert import UpsertMixin


# TODO: Validate
class HBOMaxBase(UpsertMixin, SourceMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "HBO Max"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("HBO Max", "Max")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hbomax.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        return ["play.hbomax.com", "hbomax.com"]
