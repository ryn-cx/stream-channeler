# TODO: Validate
from __future__ import annotations

from plugins.StreamChanneler.shared import StreamChannelerShared
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin_v3.initialize import BasePluginInitializer


# TODO: Validate
class StreamChannelerInitializer(BasePluginInitializer, StreamChannelerShared): ...


# TODO: Validate
class StreamChanneler(StreamChannelerShared, AbstractPlugin, register=False):
    initializer = StreamChannelerInitializer
