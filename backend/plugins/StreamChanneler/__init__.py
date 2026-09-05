# TODO: Validate
from __future__ import annotations

from plugins.StreamChanneler.base import StreamChannelerBase
from plugins.StreamChanneler.files import FileMixin
from plugins.StreamChanneler.initialize import StreamChannelerInitializer
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class StreamChanneler(StreamChannelerBase, FileMixin, AbstractPlugin, register=False):
    initializer = StreamChannelerInitializer
