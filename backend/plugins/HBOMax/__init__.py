# TODO: Validate
"""HBO Max plugin."""

from __future__ import annotations

from plugins.HBOMax.base import HBOMaxBase
from plugins.HBOMax.importer import HBOMaxImporter
from plugins.HBOMax.initialize import HBOMaxInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class HBOMax(HBOMaxBase, AbstractPlugin, register=False):
    """HBO Max plugin."""

    initializer = HBOMaxInitializer
    importer = HBOMaxImporter
