# TODO: Validate
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class BaseMediaTypeMixin:
    _media_type: str | None = None

    # TODO: Validate
    @abstractmethod
    def _set_media_type_from_title(self, title: Title) -> None: ...
