# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Tubi.shared import TubiShared
from plugins.utils.base_plugin.linker import BasePluginLinker


# TODO: Validate
class TubiLinker(TubiShared, BasePluginLinker):
    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Tubi TV", "Tubi")
