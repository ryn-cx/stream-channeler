# TODO: Validate
"""HiDive plugin."""

from __future__ import annotations

from plugins.HiDive.base import HiDiveBase
from plugins.HiDive.initialize import HiDiveInitializer
from plugins.HiDive.workers import HiDiveImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class HiDive(HiDiveBase, AbstractPlugin, register=True):
    """HiDive plugin."""

    initializer = HiDiveInitializer
    importer = HiDiveImporter
