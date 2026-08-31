# TODO: Validate
"""Adult Swim plugin."""

from __future__ import annotations

from plugins.AdultSwim.base import AdultSwimBase
from plugins.AdultSwim.import_url import AdultSwimImportURL
from plugins.AdultSwim.initialize import AdultSwimInitializer
from plugins.AdultSwim.workers import AdultSwimUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class AdultSwim(AdultSwimBase, AbstractPlugin, register=True):
    """Adult Swim plugin."""

    initializer = AdultSwimInitializer
    url_importer = AdultSwimImportURL
    updater = AdultSwimUpdater
