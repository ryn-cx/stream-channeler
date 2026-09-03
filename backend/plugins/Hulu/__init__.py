from __future__ import annotations

from plugins.Hulu.importer import HuluImporter
from plugins.Hulu.initialize import HuluInitializer
from plugins.Hulu.update import UpdateMixin
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin_v2.search import BaseCatalogueSearchMixin


class Hulu(UpdateMixin, BaseCatalogueSearchMixin, AbstractPlugin, register=True):
    initializer = HuluInitializer
    importer = HuluImporter
