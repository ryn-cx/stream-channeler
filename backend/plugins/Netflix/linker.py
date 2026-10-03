# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Netflix.shared import NetflixShared
from plugins.utils.base_plugin.linker import BasePluginLinker


# TODO: Validate
class NetflixLinker(NetflixShared, BasePluginLinker):
    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Netflix", "Netflix Standard with Ads")
