# TODO: Validate
"""Amazon Prime Video plugin."""

from __future__ import annotations

from plugins.Amazon.base import AmazonBase
from plugins.Amazon.importer import AmazonImporter
from plugins.Amazon.initialize import AmazonInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class Amazon(AmazonBase, AbstractPlugin, register=False):
    """Amazon Prime Video plugin."""

    initializer = AmazonInitializer
    importer = AmazonImporter
