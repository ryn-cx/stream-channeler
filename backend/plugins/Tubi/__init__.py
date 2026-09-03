# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from plugins.Tubi.base import TubiBase
from plugins.Tubi.importer import TubiImporter
from plugins.Tubi.initialize import TubiInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Tubi(TubiBase, AbstractPlugin, register=False):
    """Tubi plugin."""

    initializer = TubiInitializer
    importer = TubiImporter
