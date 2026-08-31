# TODO: Validate
"""HBO Max plugin."""

from __future__ import annotations

from plugins.HBOMax.base import HBOMaxBase
from plugins.HBOMax.import_url import HBOMaxImportURL
from plugins.HBOMax.initialize import HBOMaxInitializer
from plugins.HBOMax.update import HBOMaxUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class HBOMax(HBOMaxBase, AbstractPlugin, register=True):
    """HBO Max plugin."""

    initializer = HBOMaxInitializer
    url_importer = HBOMaxImportURL
    updater = HBOMaxUpdater
