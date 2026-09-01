# TODO: Validate
"""The Roku Channel plugin."""

from __future__ import annotations

from plugins.Roku.base import RokuBase
from plugins.Roku.initialize import RokuInitializer
from plugins.Roku.importer import RokuImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Roku(RokuBase, AbstractPlugin, register=True):
    """The Roku Channel plugin."""

    initializer = RokuInitializer
    importer = RokuImporter
