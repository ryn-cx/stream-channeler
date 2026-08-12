# TODO: Validate
from __future__ import annotations

from abc import abstractmethod
from typing import Any, ClassVar, override

from app.shows.models import CanonicalShow
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin
from plugins.utils.base_plugin.url import URLHandler


# TODO: Validate
class MediaTypeURLHandler[PluginT](URLHandler[PluginT]):
    media_type: ClassVar[str]


# TODO: Validate
class MediaTypeMixin:
    _media_type_value: str | None = None

    # TODO: Validate
    @abstractmethod
    def _set_media_type_from_show(self, show: Show) -> None: ...


# TODO: Validate
class MediaTypeImportMixin[HandlerT: MediaTypeURLHandler[Any]](
    MediaTypeMixin,
    URLHandlerPlugin[HandlerT],
    register=False,
):
    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: CanonicalShow | None = None,
    ) -> list[URLImportResult]:
        self._supplied_canonical_show = canonical_show
        handler = self.get_url_handler(url)
        handler.raise_if_invalid()
        self._media_type_value = handler.media_type
        show = self._import_show(handler.show_key)
        return handler.import_results(show)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._set_media_type_from_show(show)
        super().update_show(show, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        self._set_media_type_from_show(season.show)
        super().update_season(season)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._set_media_type_from_show(episode.season.show)
        super().update_episode(episode)
