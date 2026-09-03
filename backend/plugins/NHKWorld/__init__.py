# TODO: Validate
"""NHK World plugin."""

from __future__ import annotations

from plugins.NHKWorld.base import NHKWorldBase
from plugins.NHKWorld.importer import NHKWorldImporter
from plugins.NHKWorld.initialize import NHKWorldInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class NHKWorld(NHKWorldBase, AbstractPlugin, register=False):
    """NHK World plugin."""

    initializer = NHKWorldInitializer
    importer = NHKWorldImporter
