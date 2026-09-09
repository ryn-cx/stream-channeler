# TODO: Validate
from __future__ import annotations

from plugins.StreamChanneler.shared import StreamChannelerShared
from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
class StreamChanneler(StreamChannelerShared, AbstractPlugin, register=False): ...
