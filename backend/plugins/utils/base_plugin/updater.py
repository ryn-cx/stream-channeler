# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING

from app.utils import tz_datetime
from plugins.utils.base_plugin.channels import BasePluginChannelMixin
from plugins.utils.base_plugin.core import BasePluginCore
from plugins.utils.base_plugin.initialize import BaseInitializeMixin
from plugins.utils.base_plugin.plugin_files import BasePluginFilesMixin

if TYPE_CHECKING:
    from datetime import datetime

    from app.channels.models import Channel
    from app.files.models import File
    from app.plugins.models import Plugin
    from app.sources.models import Source


# TODO: Validate
class BasePluginUpdater(
    BasePluginChannelMixin,
    BaseInitializeMixin,
    BasePluginFilesMixin,
    BasePluginCore,
    ABC,
):
    # TODO: Validate
    def update_file(self, file: File) -> None:
        if file.update_at and file.update_at > tz_datetime.now():
            return
        handled = False
        if self.is_source_file(file):
            self.update_source_files()
            handled = True
        if self.is_plugin_file(file):
            self.update_plugin_files()
            handled = True
        if not handled:
            msg = f"update_file is not supported by this plugin: {file.key}"
            raise NotImplementedError(msg)

    # TODO: Validate
    def update_source_files(self) -> None:
        self._download_if_outdated(self._source_files())
        self._process_source_files()

    # TODO: Validate
    def _process_source_files(self) -> None:
        return

    # TODO: Validate
    @abstractmethod
    def _title_urls_from_files(self) -> list[str]: ...

    # TODO: Validate
    def create_initial_channel_records(self) -> None:
        self.add_new_urls_to_channel("All Titles", self._title_urls_from_files())

    # TODO: Validate
    def update_plugin_files(self) -> None:
        self._download_if_outdated(self._plugin_files())
        self._import_plugin_files()

    # TODO: Validate
    def _import_plugin_files(self) -> None:
        self.create_initial_channel_records()
        data_timestamp = min(self._plugin_files_data_timestamps())
        new_title_keys = self._title_keys_from_plugin_files()
        self._mark_mismatched_titles_as_outdated(None, new_title_keys, data_timestamp)
        self.plugin.data_timestamp = data_timestamp

    # TODO: Validate
    def update_channel(self, channel: Channel) -> None:
        self._remove_queue_entries_with_deleted_titles(channel)
        channel.update_at = tz_datetime.now() + timedelta(days=1)

    # TODO: Validate
    def update_plugin(self, plugin: Plugin) -> None:
        """Update an existing plugin in the database.

        Called when `Plugin.update_at > datetime.now()`.

        Args:
            plugin: The `Plugin` to update.

        """
        self._update_plugin(plugin)
        plugin.update_at = self._next_plugin_update_at()

    # TODO: Validate
    def _update_plugin(self, plugin: Plugin) -> None:  # noqa: ARG002
        return

    # TODO: Validate
    def update_source(self, source: Source, update_at: datetime) -> None:  # noqa: ARG002
        source.update_at = None
