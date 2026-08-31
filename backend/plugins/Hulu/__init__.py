# TODO: Validate
"""Hulu plugin."""

from __future__ import annotations

from plugins.Hulu.base import HuluBase
from plugins.Hulu.import_url import HuluImportURL
from plugins.Hulu.initialize import HuluInitializer
from plugins.Hulu.update import HuluUpdater
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Hulu(HuluBase, AbstractPlugin, register=True):
    initializer = HuluInitializer
    url_importer = HuluImportURL
    updater = HuluUpdater
