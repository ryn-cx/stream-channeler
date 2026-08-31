# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.HBOMax.base import HBOMaxBase
from plugins.utils.base_plugin_v2.workers import Updater

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show
    from plugins.utils.base_plugin_v2.base import PluginBase


# TODO: Validate
class HBOMaxUpdater(Updater, HBOMaxBase):
    # TODO: Validate
    def __init__(self, owner: PluginBase, record: Show | Season | Episode) -> None:
        super().__init__(owner, record)
        self._set_media_type_from_show(self.show)
