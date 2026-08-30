# TODO: Validate
from __future__ import annotations

from app.shows.models import Show
from plugins.AdultSwim.constants import SUBSCRIPTION
from plugins.AdultSwim.files import FileMixin


# TODO: Validate
def source_requires_auth(source_key: str) -> bool:
    return source_key == SUBSCRIPTION


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    # TODO: Validate
    def _existing_shows(self, show_key: str) -> list[Show]:
        return list(self._preload_show(show_key))
