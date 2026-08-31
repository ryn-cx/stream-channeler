from __future__ import annotations

from typing import override

from plugins.Hulu.source import SourceMixin
from plugins.Hulu.upsert import UpsertMixin
from plugins.utils.base_plugin_v2.search import CatalogueSearchMixin


class HuluBase(UpsertMixin, CatalogueSearchMixin, SourceMixin):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"
