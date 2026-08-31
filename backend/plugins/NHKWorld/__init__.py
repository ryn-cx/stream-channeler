# TODO: Validate
"""NHK World plugin."""

from __future__ import annotations

from plugins.NHKWorld.base import NHKWorldBase
from plugins.NHKWorld.initialize import NHKWorldInitializer
from plugins.NHKWorld.workers import NHKWorldImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class NHKWorld(NHKWorldBase, AbstractPlugin, register=True):
    """NHK World plugin."""

    initializer = NHKWorldInitializer
    importer = NHKWorldImporter
