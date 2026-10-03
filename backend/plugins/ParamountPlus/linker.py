# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.ParamountPlus.shared import ParamountPlusShared
from plugins.utils.base_plugin.linker import BasePluginLinker


# TODO: Validate
class ParamountPlusLinker(ParamountPlusShared, BasePluginLinker):
    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (
            "Paramount Plus",
            "Paramount+",
            "Paramount+ Amazon Channel",
            "Paramount Plus Essential",
            "Paramount Plus Premium",
        )
