# TODO: Validate
"""Paramount+ plugin."""

from __future__ import annotations

from plugins.ParamountPlus.base import ParamountPlusBase
from plugins.ParamountPlus.import_url import ParamountPlusImportURL
from plugins.ParamountPlus.initialize import ParamountPlusInitializer
from plugins.ParamountPlus.update import ParamountPlusUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class ParamountPlus(ParamountPlusBase, AbstractPlugin, register=True):
    """Paramount+ plugin."""

    initializer = ParamountPlusInitializer
    url_importer = ParamountPlusImportURL
    updater = ParamountPlusUpdater
