# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.AdultSwim.constants import FREE, SUBSCRIPTION
from plugins.AdultSwim.update import UpdateMixin
from plugins.utils.base_plugin_v2.search import BaseCatalogueSearchMixin


# TODO: Validate
class AdultSwimBase(UpdateMixin, BaseCatalogueSearchMixin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Adult Swim"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.adultswim.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "adultswim.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (FREE, SUBSCRIPTION)
