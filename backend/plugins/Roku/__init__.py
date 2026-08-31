# TODO: Validate
"""The Roku Channel plugin."""

from __future__ import annotations

from plugins.Roku.base import RokuBase
from plugins.Roku.import_url import RokuImportURL
from plugins.Roku.initialize import RokuInitializer
from plugins.Roku.update import RokuUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Roku(RokuBase, AbstractPlugin, register=True):
    """The Roku Channel plugin."""

    initializer = RokuInitializer
    url_importer = RokuImportURL
    updater = RokuUpdater
