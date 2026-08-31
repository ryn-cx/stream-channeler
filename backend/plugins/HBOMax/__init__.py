# TODO: Validate
"""HBO Max plugin."""

from __future__ import annotations

from plugins.HBOMax.base import HBOMaxBase
from plugins.HBOMax.initialize import HBOMaxInitializer
from plugins.HBOMax.workers import HBOMaxImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class HBOMax(HBOMaxBase, AbstractPlugin, register=True):
    """HBO Max plugin."""

    initializer = HBOMaxInitializer
    importer = HBOMaxImporter
