# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Hulu.constants import HuluMediaType
from plugins.Hulu.source import SourceMixin
from plugins.Hulu.upsert import UpsertMixin
from plugins.utils.base_plugin_v2.search import CatalogueSearchMixin


# TODO: Validate
class HuluBase(UpsertMixin, CatalogueSearchMixin, SourceMixin, register=False):
    _media_type: HuluMediaType

    # TODO: Validate
    @classmethod
    @override
    def plugin_key(cls) -> str:
        return "Hulu"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    # TODO: Validate
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Hulu",)

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"
