# TODO: Validate
"""Crunchyroll plugin.

Detects new media much faster than JustWatch and supports music.
"""

from __future__ import annotations

from plugins.Crunchyroll.base import CrunchyrollBase
from plugins.Crunchyroll.initialize import CrunchyrollInitializer
from plugins.Crunchyroll.workers import CrunchyrollImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Crunchyroll(CrunchyrollBase, AbstractPlugin, register=True):
    """Crunchyroll plugin.

    Detects new media much faster than JustWatch and supports music.
    """

    initializer = CrunchyrollInitializer
    importer = CrunchyrollImporter
