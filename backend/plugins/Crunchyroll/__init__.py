# TODO: Validate
# This plugin intentionally does not support movies from the movies page because it has
# been unofficially deprecated as movies are now added as a series instead.

# Current movie page example:
# https://www.crunchyroll.com/series/GMTE00335490/spy-x-family-code-white
# Deprecated movie page example:
# https://www.crunchyroll.com/videos/alphabetical?media=movies

import json
import re
from datetime import timedelta
from typing import override

from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.Crunchyroll.files import Browse, FileMixin, chirashi
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


class Crunchyroll(WatchHistoryMixin, FileMixin, register=True):
    _VERSION = "0.0.1"
    import_watch_history_file_extension = ".json"

    @override
    def initialize_source(self) -> None:
        if not self.has_source:
            latest_browse_file = self.get_latest_browse_file()
            self.source = self._upsert_source(latest_browse_file)

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Series]\n"
            "> `https://www.crunchyroll.com/series/G4PH0WXVJ/spy-x-family`\n\n"
        )

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        show_key = self.parse_url(url)
        self._validate_url(show_key, url)
        show = self._import_show(show_key)
        return [URLImportResult(show=show, is_whitelist=False)]

    @classmethod
    @override
    def parse_url(cls, url: str) -> str:
        # TODO: Add support for single episodes
        if match := re.match(cls._url_regex(), url):
            return match.group("show_key")

        msg = f"Invalid {cls.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def _validate_url(self, show_key: str, url: str) -> None:
        series_json = self.series_file(show_key)
        self.raise_invalid_url_if_no_content(series_json, url)

    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key=show_key).one_or_none():
            return show

        _cache = self._download_show_files(show_key)
        return self._upsert_show(self.source, show_key=show_key)

    @override
    def update_source(self, source: Source) -> None:
        latest_browse_file = self.get_latest_browse_file()
        new_browse_file = self.browse_file(latest_browse_file.data_timestamp)
        new_browse_file.download_if_outdated(source.update_at)
        self._process_new_browse_files(source)
        self._upsert_source(new_browse_file)

    def _process_new_browse_files(self, source: Source) -> None:
        # Preload up to seasons because seasons have their update_at values set.
        _cache = self._preload_sources(preload_seasons=True).all()

        for browse_json in self.get_incomplete_files(Browse, self.browse_file):
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
        domain_regex = cls._domain_regex()
        # Example URLs:
        #   https://www.crunchyroll.com/series/GRMG8ZQZR/one-piece
        regex_string = r"\/series\/(?P<show_key>[A-Z0-9]{9,})(?:\/|$)"
        return domain_regex + regex_string

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        """Return the episode URL for the episode_key."""
        return cls.build_url(f"watch/{episode_key}")

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return cls.build_url(f"series/{show_key}")

    def _upsert_source(self, latest_browse_file: Browse) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=self.build_url(
                "build/assets/img/favicons/favicon-v2-96x96.png",
            ),
            update_at=latest_browse_file.data_timestamp + timedelta(days=1),
            data_timestamp=latest_browse_file.data_timestamp,
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
        if len(release_dates) != 1:
            return "TV Show"
        latest_release = release_dates[0]
        if self.show_data_timestamp(show_key) > latest_release + timedelta(days=7):
            return "Movie"
        return "TV Show"

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        seasons_file = self.seasons_file(show_key)
        for i, season_data in enumerate(seasons_file.parsed().data):
            season_timestamp = self.season_data_timestamp(season_data.id, show.key)
            season = Season.get_from_memory(self.session, show, season_data.id)
            if (
                not season
                or season.data_timestamp != season_timestamp
                or season.deleted_at is not None
            ):
                season = Season(
                    key=season_data.id,
                    sort_order=i,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    data_timestamp=season_timestamp,
                    show_id=show.id,
                ).upsert(show, season)

            self._upsert_episodes(season)

        self.soft_delete_missing_seasons(show_key)

    def _upsert_episodes(self, season: Season) -> None:
        episode_timestamp = self.episode_data_timestamp("", season.key, season.show.key)
        episodes_data = self.episodes_file(season.key).parsed()
        for i, episode_data in enumerate(episodes_data.data):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_data.id,
            )
            if (
                existing_episode
                and existing_episode.data_timestamp == episode_timestamp
                and existing_episode.deleted_at is None
            ):
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
                data_timestamp=episode_timestamp,
                season_id=season.id,
            ).upsert(season, existing_episode)

        self.soft_delete_missing_episodes(season.key)

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
