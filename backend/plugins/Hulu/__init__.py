from __future__ import annotations

from plugins.Hulu.base import HuluBase
from plugins.Hulu.initialize import HuluInitializer
from plugins.Hulu.workers import HuluImporter
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Hulu(HuluBase, AbstractPlugin, register=True):
    initializer = HuluInitializer
    importer = HuluImporter
