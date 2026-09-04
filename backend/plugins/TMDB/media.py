# TODO: Validate
from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from plugins.TMDB.keys import get_media_type_and_tmdb_id
from plugins.TMDB.listed_sources import ListedSourcesMixin
from plugins.TMDB.update import SeriesUpdateMixin
from plugins.TMDB.upsert import MovieUpsertMixin
from plugins.utils.base_plugin_v2.importer import BasePluginWorker

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class TMDBMedia(ListedSourcesMixin, BasePluginWorker, ABC):
    pass


# TODO: Validate
class TMDBSeries(SeriesUpdateMixin, TMDBMedia):
    pass


# TODO: Validate
class TMDBMovie(MovieUpsertMixin, TMDBMedia):
    pass


# TODO: Validate
class MediaMixin(ListedSourcesMixin):
    # TODO: Validate
    def _media_plugin(self, show_key: str) -> TMDBMedia:
        media_type, _ = get_media_type_and_tmdb_id(show_key)
        if media_type == TMDBMediaType.movie:
            return TMDBMovie(self)
        return TMDBSeries(self)

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> Show:
        return self._media_plugin(show_key).upsert_show(
            source,
            show_key,
            canonical_show,
            force=force,
        )

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._media_plugin(show.key).update_show(show, force=force)
        self.sync_show_watch_providers(show.key)
        self._import_media_from_other_websites(show.key, show)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        media = self._media_plugin(season.show.key)
        media.update_season(season)
        media.sync_season_key_watch_providers(season.key, season.show.key)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._media_plugin(episode.season.show.key).update_episode(episode)
