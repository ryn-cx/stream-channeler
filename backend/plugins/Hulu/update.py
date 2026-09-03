# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.Hulu.media import MediaMixin
from plugins.Hulu.utils import HuluMediaType

if TYPE_CHECKING:
    from datetime import datetime

    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class UpdateMixin(MediaMixin):
    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._media_plugin(show).update_show(show, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        self._media_plugin(season.show).update_season(season)

    # TODO: Validate
    @override
    def update_episode(self, episode: Episode) -> None:
        self._media_plugin(episode.season.show).update_episode(episode)

    # TODO: Validate
    def update_source(self, source: Source, update_at: datetime) -> None:
        self.add_media_to_plugin_channels(update_at)
        self.upsert_source(source.key)

    # TODO: Validate
    def add_media_to_plugin_channels(self, update_at: datetime | None = None) -> None:
        self.genres_page_file().download_if_outdated(update_at)
        _cache = self._preload_source_files()
        self._download_outdated_files(self._source_files(), update_at)

        all_urls: list[str] = []
        movie_urls: list[str] = []
        series_urls: list[str] = []
        for genre_name, genre_href in self.genres_page_file().listed_items():
            genre_id = genre_href.rsplit("/", 1)[-1]
            genre_urls = self.genre_page_file(genre_id).media_urls()

            self.add_urls_to_plugin_channel(
                f"Hulu {genre_name}",
                f"All {genre_name} on Hulu.",
                genre_urls,
            )
            all_urls += genre_urls
            movie_urls += [
                url for url in genre_urls if f"/{HuluMediaType.MOVIE}/" in url
            ]
            series_urls += [
                url for url in genre_urls if f"/{HuluMediaType.SERIES}/" in url
            ]

        self.add_urls_to_plugin_channel("Hulu All Media", "All Media on Hulu.", all_urls)
        self.add_urls_to_plugin_channel("Hulu Movies", "All Movies on Hulu.", movie_urls)
        self.add_urls_to_plugin_channel(
            "Hulu TV Series",
            "All TV Series on Hulu.",
            series_urls,
        )
