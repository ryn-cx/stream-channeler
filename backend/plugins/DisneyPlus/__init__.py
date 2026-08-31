# TODO: Validate
"""Disney+ plugin."""

from __future__ import annotations

from plugins.DisneyPlus.base import DisneyPlusBase
from plugins.DisneyPlus.import_url import DisneyPlusImportURL
from plugins.DisneyPlus.initialize import DisneyPlusInitializer
from plugins.DisneyPlus.update import DisneyPlusUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class DisneyPlus(DisneyPlusBase, AbstractPlugin, register=True):
    """Disney+ plugin."""

    initializer = DisneyPlusInitializer
    url_importer = DisneyPlusImportURL
    updater = DisneyPlusUpdater
