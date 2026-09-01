# TODO: Validate
from __future__ import annotations

from typing import override

from plugins.Crunchyroll.base import CrunchyrollBase
from plugins.Crunchyroll.constants import MUSIC_SOURCE, VIDEO_SOURCE
from plugins.utils.base_plugin_v2.initialize import BasePluginInitializer


# TODO: Validate
class CrunchyrollInitializer(BasePluginInitializer, CrunchyrollBase):
    # TODO: Validate
    @override
    def _initialize_channels(self) -> None:
        self._video_channel()
        self._music_channel()
        self._process_new_browse_files(self._sources[VIDEO_SOURCE])
        self._process_new_music_browse_files(self._sources[MUSIC_SOURCE])
