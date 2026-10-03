# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Peacock.shared import PeacockShared
from plugins.utils.base_plugin.linker import BasePluginLinker


# TODO: Validate
class PeacockLinker(PeacockShared, BasePluginLinker):
    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Peacock", "Peacock Premium", "Peacock Premium Plus")
