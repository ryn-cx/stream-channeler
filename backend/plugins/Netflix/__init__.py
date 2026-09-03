# TODO: Validate
"""Netflix plugin."""

from __future__ import annotations

from plugins.Netflix.base import NetflixBase
from plugins.Netflix.importer import NetflixImporter
from plugins.Netflix.initialize import NetflixInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Netflix(NetflixBase, AbstractPlugin, register=False):
    """Netflix plugin."""

    initializer = NetflixInitializer
    importer = NetflixImporter
