from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.plugins.plugins.utils.base_plugin.files import BaseFile


class FileGettersMixin(ABC):
    def _newest_file_timestamp(self, files: Sequence[BaseFile[Any]]) -> datetime:
        return max(file.database_entry.data_timestamp for file in files)

    # region Files

    # The imeplementation of these functions will usually have "type: ignore[override]"
    # applied to them because the parameters will be narrowed from the abstract
    # implementation. Without this narrowing the input of the function would have to be
    # manually checked and if it does not match it would cause a runtime
    # error, but narrowing the parameters on the function turns the runtime error into a
    # type error which is easier to work with.

    @abstractmethod
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]: ...

    @abstractmethod
    def _season_files(
        self,
        season_key: str,
        show_key: str | None = None,
    ) -> Sequence[BaseFile[Any]]: ...

    @abstractmethod
    def _episode_files(
        self,
        episode_key: str,
        season_key: str | None = None,
        show_key: str | None = None,
    ) -> Sequence[BaseFile[Any]]: ...

    # endregion Files
