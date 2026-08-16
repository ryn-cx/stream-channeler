# TODO: Validate
from __future__ import annotations

from abc import abstractmethod
from typing import Any, ClassVar, override

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
    @override  # Carries the media type the URL named into the import.
    def _import_handler(
        self,
        handler: HandlerT,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        # Only the handler that matched says whether the URL named a film or a
        # series, and the id alone does not, so the type is taken from it here
        # rather than left for each plugin to remember to do.
        self._media_type_value = handler.media_type
        return super()._import_handler(handler, canonical_show, force=force)

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
