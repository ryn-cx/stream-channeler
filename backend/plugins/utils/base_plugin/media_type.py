# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import override

from app.shows.models import Show
from plugins.utils.base_plugin.plugin import ReadURLPlugin


# TODO: Validate
class MediaTypeMixin:
    _media_type_value: str | None = None

    # TODO: Validate
    @abstractmethod
    def _set_media_type_from_show(self, show: Show) -> None: ...


# TODO: Validate
class MediaTypeReadURLPlugin(MediaTypeMixin, ReadURLPlugin, ABC, register=False):
    # TODO: Validate
    @override
    def update_show(self, *, force: bool = False) -> None:
        self._set_media_type_from_show(self.show)
        super().update_show(force=force)

    # TODO: Validate
    @override
    def update_season(self) -> None:
        self._set_media_type_from_show(self.season.show)
        super().update_season()

    # TODO: Validate
    @override
    def update_episode(self) -> None:
        self._set_media_type_from_show(self.episode.season.show)
        super().update_episode()
