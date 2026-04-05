# Validated
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.plugins.plugins.utils.base_plugin.files import BaseFile


class FileGettersMixin(ABC):
    @staticmethod
    def _file_timestamp(files: Sequence[BaseFile[Any]]) -> datetime:
        """Get the timestamp of the file first file in the sequence.

        Therefore, all of the _*_files functions should have the most important file
        listed first. This will generally be the file that includes information on the
        children, for example _season_files should prioritize detecting new episodes
        over detecting changes in the season name.
        """
        return files[0].database_entry.data_timestamp

    # The imeplementation of these functions will usually have "type: ignore[override]"
    # applied to them because the parameters will be narrowed from the abstract
    # implementation. Without this narrowing the input of the function would have to be
    # manually checked and if it does not match it would cause a runtime
    # error, but narrowing the parameters on the function turns the runtime error into a
    # type error which is easier to work with.

    @abstractmethod
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the show.

        Parameters are ordered from most specific to least specific to make it easier to
        call the function with just the required parameters.
        """

    @abstractmethod
    def _season_files(
        self,
        season_key: str,
        show_key: str | None = None,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the season.

        Parameters are ordered from most specific to least specific to make it easier to
        call the function with just the required parameters.
        """

    @abstractmethod
    def _episode_files(
        self,
        episode_key: str,
        season_key: str | None = None,
        show_key: str | None = None,
    ) -> Sequence[BaseFile[Any]]:
        """Return the files associated with the episode.

        Parameters are ordered from most specific to least specific to make it easier to
        call the function with just the required parameters.
        """
