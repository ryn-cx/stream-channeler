# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import override

from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.utils import build_url
from plugins.utils.base_plugin.importer import BaseImporter


# TODO: Validate
class CrunchyrollImporter(CrunchyrollShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @abstractmethod
    def _source_update_interval(cls) -> timedelta: ...

    # TODO: Validate
    @staticmethod
    def title_url(title_key: str) -> str:
        return build_url(f"series/{title_key}")

    # TODO: Validate
    @override
    def _next_source_update_at(self) -> datetime:
        return (
            min(self._source_files_data_timestamps()) + self._source_update_interval()
        )
