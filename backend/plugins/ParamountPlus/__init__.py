# TODO: Validate
"""Paramount+ plugin."""

from __future__ import annotations

from plugins.ParamountPlus.base import ParamountPlusBase
from plugins.ParamountPlus.importer import ParamountPlusImporter
from plugins.ParamountPlus.initialize import ParamountPlusInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class ParamountPlus(ParamountPlusBase, AbstractPlugin, register=False):
    """Paramount+ plugin."""

    initializer = ParamountPlusInitializer
    importer = ParamountPlusImporter
