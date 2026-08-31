# TODO: Validate
from __future__ import annotations

from abc import ABC

from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin_v2.core import PluginCore
from plugins.utils.base_plugin_v2.watch import WatchMixin


# TODO: Validate
class FacadePlugin(PluginCore, WatchMixin, AbstractPlugin, ABC, register=False):
    pass
