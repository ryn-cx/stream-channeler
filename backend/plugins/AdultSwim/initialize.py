# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.utils import tz_datetime
from plugins.AdultSwim.base import AdultSwimBase
from plugins.utils.base_plugin_v2.initialize import PluginInitializer

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
class AdultSwimInitializer(PluginInitializer, AdultSwimBase):
    # TODO: Validate
    @classmethod
    @override
    def initialize_sources(cls, session: Session, plugin: Plugin) -> None:
        super().initialize_sources(session, plugin)
        if plugin.update_at is None:
            plugin.update_at = tz_datetime.now()
