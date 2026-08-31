# TODO: Validate
"""Pluto TV plugin."""

from __future__ import annotations

from plugins.Pluto.base import PlutoBase
from plugins.Pluto.initialize import PlutoInitializer
from plugins.Pluto.workers import PlutoImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Pluto(PlutoBase, AbstractPlugin, register=True):
    """Pluto TV plugin."""

    initializer = PlutoInitializer
    importer = PlutoImporter
