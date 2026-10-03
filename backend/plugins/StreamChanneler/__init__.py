# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.StreamChanneler.linker import StreamChannelerLinker
from plugins.StreamChanneler.shared import StreamChannelerShared
from plugins.StreamChanneler.updater import StreamChannelerUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.watch_history import BaseWatchHistoryDispatcherMixin

if TYPE_CHECKING:
    from app.users.models import User
    from app.watches.schemas import WatchExportEntry


# TODO: Validate
class StreamChanneler(
    StreamChannelerShared,
    BaseWatchHistoryDispatcherMixin,
    BasePlugin,
    register=True,
):
    import_watch_history_file_extension = ".json"

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[StreamChannelerUpdater]:
        return StreamChannelerUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[StreamChannelerLinker]:
        return StreamChannelerLinker

    # TODO: Validate
    def _stream_channeler_updater(self) -> StreamChannelerUpdater:
        return StreamChannelerUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _watch_history_importer(self) -> StreamChannelerUpdater:
        return self._stream_channeler_updater()

    # TODO: Validate
    def export_watch_history(self, user: User) -> list[WatchExportEntry]:
        return self._stream_channeler_updater().export_watch_history(user)
