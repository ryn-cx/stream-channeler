from __future__ import annotations

from typing import override

from plugins.Hulu.update import UpdateMixin
from plugins.utils.base_plugin_v2.search import BaseCatalogueSearchMixin


class HuluBase(UpdateMixin, BaseCatalogueSearchMixin):
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
