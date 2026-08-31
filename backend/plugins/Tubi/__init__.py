# TODO: Validate
"""Tubi plugin."""

from __future__ import annotations

from plugins.Tubi.base import TubiBase
from plugins.Tubi.import_url import TubiImportURL
from plugins.Tubi.initialize import TubiInitializer
from plugins.Tubi.update import TubiUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Tubi(TubiBase, AbstractPlugin, register=True):
    """Tubi plugin."""

    initializer = TubiInitializer
    url_importer = TubiImportURL
    updater = TubiUpdater
