# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin_v2.initialize import PluginInitializer
from plugins.WatchMode.base import WatchModeBase

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
class WatchModeInitializer(PluginInitializer, WatchModeBase):
    # Watchmode holds no listing of its own, so it has no `Source` to create.
    # TODO: Validate
    @classmethod
    @override
    def initialize_sources(cls, session: Session, plugin: Plugin) -> None:
        return
