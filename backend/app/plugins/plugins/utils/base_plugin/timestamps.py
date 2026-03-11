from abc import ABC
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.plugins.plugins.utils.base_plugin.files import BaseFile


class TimestampsMixin(ABC):
    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _source_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the source files."""
        return self._oldest_file_timestamp(self._source_files(*_args, **_kwargs))

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _show_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the show files."""
        return self._oldest_file_timestamp(self._show_files(*_args, **_kwargs))

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _season_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the season files."""
        return self._oldest_file_timestamp(self._season_files(*_args, **_kwargs))

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _episode_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the episode files."""
        return self._oldest_file_timestamp(self._episode_files(*_args, **_kwargs))

    def _oldest_file_timestamp(self, files: Sequence[BaseFile[Any]]) -> datetime:
        return min(file.get_data_timestamp() for file in files)

    def _source_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]: ...  # noqa: ANN401

    def _show_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]: ...  # noqa: ANN401

    def _season_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]: ...  # noqa: ANN401

    def _episode_files(
        self,
        *_args: Any,
        **_kwargs: Any,
    ) -> Sequence[BaseFile[Any]]: ...
