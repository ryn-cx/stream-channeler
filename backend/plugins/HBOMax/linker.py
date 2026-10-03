# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.HBOMax.shared import HBOMaxShared
from plugins.utils.base_plugin.linker import BasePluginLinker


# TODO: Validate
class HBOMaxLinker(HBOMaxShared, BasePluginLinker):
    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("HBO Max", "Max")
