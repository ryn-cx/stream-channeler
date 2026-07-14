"""Crunchyroll plugin."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger
from pydantic import BaseModel

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.Crunchyroll.files import BrowseSeries, FileMixin, chirashi
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    PluginSearchResult,
    PluginSearchResults,
    URLImportResult,
)
from plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
    WatchHistoryMixin,
)

if TYPE_CHECKING:
    from plugins.Crunchyroll import Crunchyroll


class SeriesURL(BaseModel):
    url: str
    show_key: str

    def get_show_key(self, plugin: Crunchyroll) -> str:  # noqa: ARG002
        return self.show_key

    def generate_url_import_results(self, show: Show) -> list[URLImportResult]:
        return [URLImportResult(show=show, is_whitelist=False)]


class EpisodeURL(BaseModel):
    url: str
    episode_key: str

    def get_show_key(self, plugin: Crunchyroll) -> str:
        objects_file = plugin.objects_file(self.episode_key)
        objects_file.download_if_outdated()
        return objects_file.parsed().data[0].episode_metadata.series_id

    def generate_url_import_results(self, show: Show) -> list[URLImportResult]:
        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self.episode_key:
                    return [
                        URLImportResult(
                            show=show,
                            episodes=[episode],
                            is_whitelist=True,
                        ),
                    ]

        msg = f"Episode {self.episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)


class Crunchyroll(WatchHistoryMixin, FileMixin, register=True):
    """Crunchyroll plugin."""

    _VERSION = "0.0.1"
    import_watch_history_file_extension = ".json"

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.crunchyroll.com/series/GEXH3W29Z/compass20-animation-project`\n\n"
        )

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed_url = self._parse_url(url)
        show_key = parsed_url.get_show_key(self)
        self._validate_url(show_key, url)
        show = self._import_show(show_key)
        return parsed_url.generate_url_import_results(show)

    @override
    def _parse_url(self, url: str) -> SeriesURL | EpisodeURL:
        if match := re.match(self._series_url_regex(), url):
            return SeriesURL(url=url, show_key=match.group("show_key"))

        if match := re.match(self._watch_url_regex(), url):
            return EpisodeURL(url=url, episode_key=match.group("episode_key"))

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    def _validate_url(self, show_key: str, url: str) -> None:
        series_json = self.series_file(show_key)
        self._raise_if_invalid_file(series_json, url)

    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key).one_or_none():
            return show

        _cache = self._download_show_files_and_children(show_key)
        return self._upsert_show(self.source, show_key=show_key)

    @override
    def update_source(self, source: Source) -> None:
        latest_browse_file = self.get_latest_browse_file()
        new_browse_file = self.browse_file(latest_browse_file.data_timestamp)
        new_browse_file.download_if_outdated()
        self._process_new_browse_files(source)
        self._upsert_source()

    def _process_new_browse_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_seasons=True).all()

        for browse_json in self.get_incomplete_files(BrowseSeries, self.browse_file):
            logger.info("Processing browse file: {}", browse_json.database_record.key)
            for release in browse_json.datums():
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

    @classmethod
    @override
    def _domain(cls) -> str:
        return "crunchyroll.com"

    @classmethod
    @override
    def _url_regex(cls) -> str:
        return f"(?:{cls._series_url_regex()}|{cls._watch_url_regex()})"

    @classmethod
    def _series_url_regex(cls) -> str:
        # Example URLs:
        #   https://www.crunchyroll.com/series/GRMG8ZQZR/one-piece
        return cls._domain_regex() + r"\/series\/(?P<show_key>[A-Z0-9]{9,})(?:\/|$)"

    @classmethod
    def _watch_url_regex(cls) -> str:
        # Example URLs:
        #   https://www.crunchyroll.com/watch/GE00375439JAJP/taiyaki-takoyaki-odango
        return cls._domain_regex() + r"\/watch\/(?P<episode_key>[A-Z0-9]{9,})(?:\/|$)"

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        """Return the episode URL for the episode_key."""
        return cls.build_url(f"watch/{episode_key}")

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    def _upsert_source(self) -> Source:
        source_timestamp = self.source_data_timestamp(self.plugin_key())
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())

        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=self.build_url(
                "build/assets/img/favicons/favicon-v2-96x96.png",
            ),
            data_timestamp=source_timestamp,
            update_at=source_timestamp + timedelta(days=1),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        series_data = self.series_file(show_key).parsed().data[0]
        show = Show(
            key=series_data.id,
            name=series_data.title,
            description=series_data.description,
            url=self._show_url(series_data.id),
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
            media_type=self._guess_media_type(show_key),
        ).upsert(source, existing_show)

        self._upsert_seasons(show, show_key)

        self._set_weekly_updates_from_episodes(show)

        return show

    def _guess_media_type(self, show_key: str) -> str:
        """Guess media type based on the number of episodes and their release dates."""
        release_dates = [
            episode_data.premium_available_date
            for season_key in self._season_keys_from_file(show_key)
            for episode_data in self.episodes_file(season_key).parsed().data
        ]
        data_timestamp = self.show_data_timestamp(show_key)
        next_episode_timestamp = release_dates[0] + timedelta(days=7)
        if len(release_dates) == 1 and data_timestamp > next_episode_timestamp:
            return "Movie"
        return "TV Show"

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        seasons_file = self.seasons_file(show_key)
        for i, season_data in enumerate(seasons_file.parsed().data):
            if season_check := self._season_check(show, season_data.id, show.key):
                season = Season(
                    key=season_data.id,
                    sort_order=i,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    data_timestamp=season_check.data_timestamp,
                    show_id=show.id,
                ).upsert(show, season_check.record)
            else:
                season = season_check.record

            self._upsert_episodes(season)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_episodes(self, season: Season) -> None:
        episodes_data = self.episodes_file(season.key).parsed()
        for i, episode_data in enumerate(episodes_data.data):
            episode_check = self._episode_check(
                episode_data.id,
                season,
                season.show.key,
            )
            if not episode_check:
                continue
            Episode(
                key=episode_data.id,
                url=self._episode_url(episode_data.id),
                sort_order=i,
                description=episode_data.description,
                image_url=episode_data.images.thumbnail[0][-1].source,
                episode_number=episode_data.episode_number,
                name=episode_data.title,
                release_date=episode_data.premium_available_date,
                air_date=episode_data.episode_air_date,
                duration=episode_data.duration_ms // 1000,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert(season, episode_check.record)

        self.soft_delete_missing_episodes(season.key)

    # TODO: Add searching for other media types.
    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        series = chirashi().search.extract_series(search_file.parsed())
        results = [
            PluginSearchResult(
                title=item.title,
                url=self._show_url(item.id),
                year=item.series_metadata.series_launch_year,
                image_url=item.images.poster_tall[0][1].source,
                media_type="TV Show",
            )
            for item in series
        ]
        return PluginSearchResults(has_source_selection=False, results=results)

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
