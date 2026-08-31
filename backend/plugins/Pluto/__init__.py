# TODO: Validate
"""Pluto TV plugin."""

from __future__ import annotations

from plugins.Pluto.base import PlutoBase
from plugins.Pluto.import_url import PlutoImportURL
from plugins.Pluto.initialize import PlutoInitializer
from plugins.Pluto.update import PlutoUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Pluto(PlutoBase, AbstractPlugin, register=True):
    """Pluto TV plugin."""

    initializer = PlutoInitializer
    url_importer = PlutoImportURL
    updater = PlutoUpdater
