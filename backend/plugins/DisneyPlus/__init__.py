# TODO: Validate
"""Disney+ plugin."""

from __future__ import annotations

from plugins.DisneyPlus.base import DisneyPlusBase
from plugins.DisneyPlus.initialize import DisneyPlusInitializer
from plugins.DisneyPlus.importer import DisneyPlusImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class DisneyPlus(DisneyPlusBase, AbstractPlugin, register=True):
    """Disney+ plugin."""

    initializer = DisneyPlusInitializer
    importer = DisneyPlusImporter
