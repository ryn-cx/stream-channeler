# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.canonical_media.service.identifiers import canonical_show_ids_by_key
from plugins.Hulu.constants import MOVIE_URL_REGEX, SERIES_URL_REGEX
from plugins.Hulu.media import MediaMixin
from plugins.Hulu.utils import HuluMediaType, listed_items, media_urls

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from uuid import UUID

    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source


# TODO: Validate
class UpdateMixin(MediaMixin):
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        self._media_plugin(show).update_show(show, force=force)

    @override
    def update_season(self, season: Season) -> None:
        self._media_plugin(season.show).update_season(season)

    @override
    def update_episode(self, episode: Episode) -> None:
        self._media_plugin(episode.season.show).update_episode(episode)

    def update_source(self, source: Source, update_at: datetime) -> None:
        self.add_media_to_plugin_channels(update_at)
        self.upsert_source(source.key)

    # TODO: Validate
    def add_media_to_plugin_channels(self, update_at: datetime | None = None) -> None:
        self.genres_file().download_if_outdated(update_at)
        _cache = self._preload_source_files()
        self._download_outdated_files(self._source_files(), update_at)

        all_urls: list[str] = []
        movie_urls: list[str] = []
        series_urls: list[str] = []
        for genre_name, genre_href in listed_items(
            self.genres_file().parsed(),
        ):
            genre_id = genre_href.rsplit("/", 1)[-1]
            genre_urls = media_urls(self.genre_file(genre_id).parsed())

            self._replace_plugin_channel_media(
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

        self._replace_plugin_channel_media(
            "Hulu All Media",
            "All Media on Hulu.",
            all_urls,
        )
        self._replace_plugin_channel_media(
            "Hulu Movies",
            "All Movies on Hulu.",
            movie_urls,
        )
        self._replace_plugin_channel_media(
            "Hulu TV Series",
            "All TV Series on Hulu.",
            series_urls,
        )

    # TODO: Validate
    def _canonical_show_ids(self, urls: Sequence[str]) -> set[UUID]:
        show_keys: set[str] = set()
        for url in urls:
            if match := re.search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url):
                show_keys.add(match.group("series_key") or match.group("movie_key"))
        return {
            show_id
            for show_ids in canonical_show_ids_by_key(self.session, show_keys).values()
            for show_id in show_ids
        }

    # TODO: Validate
    def _replace_plugin_channel_media(
        self,
        channel_name: str,
        channel_description: str,
        urls: Sequence[str],
    ) -> None:
        channel = self.add_urls_to_plugin_channel(
            channel_name,
            channel_description,
            urls,
        )

        canonical_show_ids = self._canonical_show_ids(urls)
        for channel_show in list(channel.shows):
            if channel_show.canonical_show_id not in canonical_show_ids:
                self.session.delete(channel_show)
        self.session.commit()
