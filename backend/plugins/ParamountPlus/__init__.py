# TODO: Validate
"""Paramount+ plugin."""

from __future__ import annotations

from plugins.ParamountPlus.base import ParamountPlusBase
from plugins.ParamountPlus.initialize import ParamountPlusInitializer
from plugins.ParamountPlus.workers import ParamountPlusImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class ParamountPlus(ParamountPlusBase, AbstractPlugin, register=True):
    """Paramount+ plugin."""

    initializer = ParamountPlusInitializer
    importer = ParamountPlusImporter
