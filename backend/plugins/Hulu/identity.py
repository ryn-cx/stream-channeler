# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.utils.base_plugin_v2.base import BasePlugin


# TODO: Validate
class HuluIdentity(BasePlugin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

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
