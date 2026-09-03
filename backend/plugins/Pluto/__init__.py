# TODO: Validate
"""Pluto TV plugin."""

from __future__ import annotations

from plugins.Pluto.base import PlutoBase
from plugins.Pluto.importer import PlutoImporter
from plugins.Pluto.initialize import PlutoInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Pluto(PlutoBase, AbstractPlugin, register=False):
    """Pluto TV plugin."""

    initializer = PlutoInitializer
    importer = PlutoImporter
