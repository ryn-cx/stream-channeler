# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

from plugins.Crunchyroll.base import CrunchyrollBase
from plugins.Crunchyroll.import_url import CrunchyrollImportURL
from plugins.Crunchyroll.initialize import CrunchyrollInitializer
from plugins.Crunchyroll.workers import CrunchyrollUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Crunchyroll(CrunchyrollBase, AbstractPlugin, register=True):
    """Crunchyroll plugin.

    Detects new media much faster than JustWatch and supports music.
    """

    initializer = CrunchyrollInitializer
    url_importer = CrunchyrollImportURL
    updater = CrunchyrollUpdater
