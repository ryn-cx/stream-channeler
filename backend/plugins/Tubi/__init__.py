# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from plugins.Tubi.base import TubiBase
from plugins.Tubi.initialize import TubiInitializer
from plugins.Tubi.workers import TubiImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Tubi(TubiBase, AbstractPlugin, register=True):
    """Tubi plugin."""

    initializer = TubiInitializer
    importer = TubiImporter
