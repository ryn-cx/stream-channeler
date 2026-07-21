# TODO: Validate
"""Crunchyroll plugin."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Literal, override

from chirashi.search import models as search_models
from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.Crunchyroll.files import BrowseSeries, FileMixin
from plugins.Crunchyroll.handlers import (
    CrunchyrollURLHandler,
    EpisodeURLHandler,
    SeriesURLHandler,
)
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin
from plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
    WatchHistoryMixin,
)


class Crunchyroll(
    WatchHistoryMixin,
    FileMixin,
    URLHandlerPlugin[CrunchyrollURLHandler],
    register=True,
):
    """Crunchyroll plugin."""

    _VERSION = "0.0.1"
    import_watch_history_file_extension = ".json"
    TMDB_PROVIDER_NAMES = ("Crunchyroll",)

    _URL_HANDLERS = (SeriesURLHandler, EpisodeURLHandler)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return cls.build_url(f"watch/{episode_key}")

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.crunchyroll.com/series/GEXH3W29Z/compass20-animation-project`\n\n"
        )

    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_browse_file = self.browse_file(source.data_timestamp)
        new_browse_file.download_if_outdated()
        self._process_new_browse_files(source)
        self._upsert_source()

    def _process_new_browse_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()

        for browse_json in self.get_incomplete_files(BrowseSeries, self.browse_file):
            logger.info("Processing browse file: {}", browse_json.database_record.key)
            for release in browse_json.extract_datums():
                if show := Show.get_from_memory(self.session, source, release.id):
                    logger.info("Matched show: {}", show.name or release.id)
                    # last_public appears to represent the last time a public change
                    # was made to the show's data. There is no way to detect what
                    # season the update is for so both show and season need to be set
                    # to be updated because the season will detect new episodes for
                    # existing seasons and the shows will detect new seasons.
                    show.set_update_at(release.last_public)
                    for season in show.seasons:
                        season.set_update_at(release.last_public)

            browse_json.database_record.extra = "Completed"

    def _upsert_source(self) -> Source:
        if not ( latest_browse_file := self.get_newest_browse_file()):
            latest_browse_file = self.browse_file(tz_datetime.now())
            latest_browse_file.download_if_outdated()
        data_timestamp = latest_browse_file.data_timestamp

        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=self.build_url(
                "build/assets/img/favicons/favicon-v2-96x96.png",
            ),
            data_timestamp=data_timestamp,
            update_at=data_timestamp + timedelta(days=1),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        series_data = self.series_file(show_key).parsed().data[0]

        show = Show(
            key=series_data.id,
            name=series_data.title,
            description=series_data.description,
            media_type="Movie" if "type:movie" in series_data.keywords else "Series",
            url=self._show_url(series_data.id),
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        )

        tmdb_media_type: Literal["movie", "tv"] = (
            "movie" if show.media_type == "Movie" else "tv"
        )
        tmdb_show_id = self._fetch_tmdb_id(show_key, existing_show)
        show = self.tmdb.tmdb_merge_show(show, tmdb_show_id, tmdb_media_type)
        show_files = self._show_files(show_key)
        show = show.upsert_and_set_update_at(source, existing_show, show_files)
        self._upsert_seasons(show, show_key)
        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        media_type: Literal["movie", "tv"] = (
            "movie" if show.media_type == "Movie" else "tv"
        )
        seasons_file = self.seasons_file(show_key)
        for i, season_data in enumerate(seasons_file.parsed().data):
            if season_check := self._season_check(show, season_data.id, show.key):
                season = Season(
                    key=season_data.id,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    sort_order=i,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                )
                season = self.tmdb.tmdb_merge_season(
                    season,
                    show.tmdb_id,
                    season_data.season_number,
                    media_type,
                )
                season = season.upsert_and_set_update_at(
                    show,
                    season_check.record,
                    self._season_files(season_data.id, show_key),
                )
            else:
                season = season_check.record

            self._upsert_episodes(season)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_episodes(self, season: Season) -> None:
        show_key = season.show.key
        media_type: Literal["movie", "tv"] = (
            "movie" if season.show.media_type == "Movie" else "tv"
        )
        episodes_data = self.episodes_file(season.key).parsed()
        for i, episode_data in enumerate(episodes_data.data):
            episode_check = self._episode_check(
                episode_data.id,
                season,
                show_key,
            )
            if not episode_check:
                continue
            episode = Episode(
                key=episode_data.id,
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self._episode_url(episode_data.id),
                description=episode_data.description,
                image_url=episode_data.images.thumbnail[0][-1].source,
                duration=episode_data.duration_ms // 1000,
                sort_order=i,
                release_date=episode_data.premium_available_date,
                air_date=episode_data.episode_air_date,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            )
            episode = self.tmdb.tmdb_merge_episode(
                episode,
                season.show.tmdb_id,
                season.season_number,
                episode_data.episode_number,
                media_type,
            )
            episode.upsert_and_set_update_at(
                season,
                episode_check.record,
                self._episode_files(episode_data.id, season.key, show_key),
            )

        self.soft_delete_missing_episodes(season.key)

    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()
        items = [
            item
            for datum in parsed.data
            if datum.type != "top_results"
            for item in datum.items
        ]
        items.sort(key=lambda item: item.search_metadata.score, reverse=True)
        results = [
            PluginSearchResult(
                title=item.title,
                url=self._show_url(item.id),
                year=item.series_metadata.series_launch_year
                if item.series_metadata
                else None,
                image_url=self._search_image_url(item.images),
                media_type=item.type.replace("_", " ").title(),
            )
            for item in items
        ]
        return PluginSearchResults(results=results)

    @staticmethod
    def _search_image_url(images: search_models.Images) -> str | None:
        for group in (
            images.poster_tall,
            images.promo_image,
            images.poster_wide,
            images.thumbnail,
        ):
            if group:
                variants = group[0]
                image = variants[1] if isinstance(variants, list) else variants
                return image.source
        return None

    @classmethod
    @override
    def import_watch_history_instructions(cls) -> str:
        return (
            "1. Use [Itamae](https://github.com/ryn-cx/itamae) to download "
            "your Crunchyroll watch history\n"
            "2. Upload the file here"
        )

    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        return [
            ParsedWatchEntry(
                episode_key=entry["id"],
                watch_date=tz_datetime.fromisoformat(entry["date_played"]),
                import_result=WatchImportResult(
                    show=entry["panel"]["episode_metadata"]["series_title"],
                    show_url=self._show_url(
                        entry["panel"]["episode_metadata"]["series_id"],
                    ),
                    episode=entry["panel"]["title"],
                    episode_url=self._episode_url(entry["id"]),
                ),
            )
            for entry in json.loads(content)
        ]
