# TODO: Validate
"""Netflix plugin."""

from __future__ import annotations

from plugins.Netflix.base import NetflixBase
from plugins.Netflix.import_url import NetflixImportURL
from plugins.Netflix.initialize import NetflixInitializer
from plugins.Netflix.update import NetflixUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Netflix(NetflixBase, AbstractPlugin, register=True):
    """Netflix plugin."""

    initializer = NetflixInitializer
    url_importer = NetflixImportURL
    updater = NetflixUpdater
