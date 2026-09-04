# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, override

from plugins.utils.base_plugin_v2.base import BasePlugin
from plugins.utils.base_plugin_v2.files import BaseFile


# StreamChanneler does not use files, so these abstract methods are no-ops.
# TODO: Validate
class FileMixin(BasePlugin):
    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return []

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return []

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        return []
