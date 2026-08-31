# TODO: Validate
"""HiDive plugin."""

from __future__ import annotations

from plugins.HiDive.base import HiDiveBase
from plugins.HiDive.import_url import HiDiveImportURL
from plugins.HiDive.initialize import HiDiveInitializer
from plugins.HiDive.update import HiDiveUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class HiDive(HiDiveBase, AbstractPlugin, register=True):
    """HiDive plugin."""

    initializer = HiDiveInitializer
    url_importer = HiDiveImportURL
    updater = HiDiveUpdater
