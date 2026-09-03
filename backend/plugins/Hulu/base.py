from __future__ import annotations

from plugins.Hulu.update import UpdateMixin
from plugins.utils.base_plugin_v2.search import BaseCatalogueSearchMixin


# TODO: Validate
class HuluBase(UpdateMixin, BaseCatalogueSearchMixin):
    pass
