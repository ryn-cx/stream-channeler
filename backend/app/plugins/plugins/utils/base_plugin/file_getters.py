from abc import ABC
from collections.abc import Sequence
from typing import Any

from app.plugins.plugins.utils.base_plugin.files import BaseFile


class FileGettersMixin(ABC):
    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _source_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]:  # noqa: ANN401
        """Returns the files required to detect changes to a show."""
        return []

    # ANN401 - This is a abstractmethod, it's fine to allow any as the implementation
    # can choose what the args and kwargs are.
    def _show_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]:  # noqa: ANN401
        """Returns the files required to detect changes to a show."""
        return []

    # ANN401 - This is a abstractmethod, it's fine to allow any as the implementation
    # can choose what the args and kwargs are.
    def _season_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]:  # noqa: ANN401
        """Returns the files required to detect changes to a season."""
        return []

    # ANN401 - This is a abstractmethod, it's fine to allow any as the implementation
    # can choose what the args and kwargs are.
    def _episode_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile[Any]]:  # noqa: ANN401
        """Returns the files required to detect changes to an episode."""
        return []
