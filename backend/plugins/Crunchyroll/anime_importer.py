# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.files.models import File
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from plugins.Crunchyroll.constants import (
    EPISODE_URL_REGEX,
    SERIES_URL_REGEX,
)
from plugins.Crunchyroll.files import BrowseSeries
from plugins.Crunchyroll.shared import CrunchyrollShared
from plugins.Crunchyroll.utils import (
    build_url,
    episode_image,
    episode_thumbnail,
    is_movie,
    title_image,
    title_poster,
    title_poster_thumbnail,
    title_thumbnail,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from chirashi.browse_series.models import Datum as BrowseSeriesDatum

    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class CrunchyrollAnimeFiles(CrunchyrollShared, BaseImporter, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new seasons.
            self.seasons_file(title_key),
            # Required to detect changes to the title.
            self.series_file(title_key),
            self.categories_file(title_key),
            self.similar_to_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new episodes.
            self.season_episodes_file(season_key),
            # Required to detect changes to the season.
            self.seasons_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode.
        return [self.season_episodes_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            season_data.id for season_data in self.seasons_file(title_key).parsed().data
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.id
            for season_key in season_keys
            for episode in self.season_episodes_file(season_key).parsed().data
        ]

    # TODO: Validate
    def browse_file(
        self,
        browse: datetime | File,
    ) -> BrowseSeries:
        """Return data for recently aired titles."""
        if isinstance(browse, File):
            return self._cached_file(
                BrowseSeries,
                BrowseSeries.file_to_unique_identifier(browse),
            )
        return self._cached_file(BrowseSeries, str(browse))

    # TODO: Validate
    def newest_browse_file(self) -> BrowseSeries:
        if file := self.latest_file_record(BrowseSeries):
            return self.browse_file(file)
        newest_browse_file = self.browse_file(tz_datetime.now())
        newest_browse_file.download_if_outdated()
        return newest_browse_file

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        return [self.newest_browse_file()]


class CrunchyrollAnimeChannels(CrunchyrollAnimeFiles, ABC):
    @classmethod
    @override
    def title_url(cls, title_key: str) -> str:
        return build_url(f"series/{title_key}")

    @override
    def create_initial_channel_records(self) -> None:
        catalogue_file = self.catalogue_file()
        catalogue_file.download_if_outdated()
        self._add_titles_to_all_titles_channel(
            release.id for release in catalogue_file.datums()
        )

    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # This should not be possible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        category_titles = ["All Titles"]
        categories = self.categories_file(title.key).parsed().data
        category_titles.extend(category.localization.title for category in categories)
        for channel_key in category_titles:
            self.add_new_urls_to_channel(channel_key, [title.url])

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        data = self.similar_to_file(title.key).parsed().data
        return [self.title_url(datum.id) for datum in data]

    # TODO: Validate
    def _add_similar_titles_to_all_titles_channel(self, title_key: str) -> None:
        data = self.similar_to_file(title_key).parsed().data
        self._add_titles_to_all_titles_channel(datum.id for datum in data)

    # TODO: Validate
    def _create_channel_records_from_incomplete_browse_files(self) -> None:
        for browse_json in self._incomplete_files(BrowseSeries, self.browse_file):
            self._add_titles_to_all_titles_channel(
                release.id for release in browse_json.datums()
            )
            browse_json.clear_status()


# TODO: Validate
class CrunchyrollAnimeUpsert(CrunchyrollAnimeChannels, ABC):
    @staticmethod
    def episode_url(episode_key: str) -> str:
        return build_url(f"watch/{episode_key}")

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        series_data = self.series_file(title_key).parsed()
        upserted_title = Title(
            key=series_data.id,
            name=series_data.title,
            description=series_data.description,
            media_type=MediaType.movie if is_movie(series_data) else MediaType.series,
            url=self.title_url(series_data.id),
            image_url=title_image(series_data.images),
            thumbnail_url=title_thumbnail(series_data.images),
            poster_url=title_poster(series_data.images),
            poster_thumbnail_url=title_poster_thumbnail(series_data.images),
            year=series_data.series_launch_year,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(
            category.localization.title
            for category in self.categories_file(title_key).parsed().data
        )

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)
        self._add_similar_titles_to_all_titles_channel(upserted_title.key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        seasons_file = self.seasons_file(title.key)
        for sort_order, season_data in enumerate(seasons_file.parsed().data):
            existing_season = Season.get_from_memory(
                self.session,
                title,
                season_data.id,
            )
            upserted_season = Season(
                key=season_data.id,
                name=season_data.title,
                season_number=season_data.season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_data.id,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key)
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        parsed_season_episodes = self.season_episodes_file(season.key).parsed()
        for sort_order, episode_data in enumerate(parsed_season_episodes.data):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_data.id,
            )
            Episode(
                key=episode_data.id,
                watch_identifier=watch_identifier(
                    self.plugin_name(),
                    episode_data.id,
                ),
                name=episode_data.title,
                episode_number=episode_data.episode_number,
                url=self.episode_url(episode_data.id),
                description=episode_data.description,
                image_url=episode_image(episode_data.images),
                thumbnail_url=episode_thumbnail(episode_data.images),
                duration=episode_data.duration_ms // 1000,
                sort_order=sort_order,
                air_date=episode_data.episode_air_date,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_data.id,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class CrunchyrollAnimeImporter(CrunchyrollAnimeUpsert):
    """Plugin for handling Crunchyroll anime and live-action series.

    Named CrunchyRollAnime because the majority of the titles it handles will be anime
    and this name makes it as clear as possible that it does not import music content.
    """

    # TODO: Validate
    @override
    def _next_source_update_at(self) -> datetime:
        # The page lists episodes from newest to oldest, daily checks work best for
        # this.
        return self._source_files_data_timestamp() + timedelta(days=1)

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, EPISODE_URL_REGEX)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        domain_regex = self._domains_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.series_file(title_key), url)
            return ParsedURL(title_key)

        if match := re.match(domain_regex + EPISODE_URL_REGEX, url):
            episode_key = match.group("episode_key")
            objects_file = self.objects_file(episode_key)
            self.raise_invalid_url_if_no_content(objects_file, url)

            # Episodes for different regions have different keys. The title is always
            # imported using the original region for consistency.
            for version in objects_file.parsed().episode_metadata.versions:
                if version.original:
                    episode_key = version.guid
                    break

            original_file = self.objects_file(episode_key)
            self.raise_invalid_url_if_no_content(original_file, url)
            return ParsedURL(
                original_file.parsed().episode_metadata.series_id,
                episode_key=episode_key,
            )

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _mark_new_titles_as_outdated(self, releases: list[BrowseSeriesDatum]) -> None:
        _cache = self._preload_sources(self.source_name(), preload_seasons=True).all()
        for release in releases:
            if title := Title.get_from_memory(
                self.session,
                self._sources[self.source_name()],
                release.id,
            ):
                # last_public appears to represent the last time a public change
                # was made to the title's data. There is no way to detect what
                # season the update is for so both title and season need to be set
                # to be updated because the season will detect new episodes for
                # existing seasons and the titles will detect new seasons.
                title.set_update_at(release.last_public)
                for season in title.seasons:
                    season.set_update_at(release.last_public)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        self._download_if_outdated(self._source_files(), update_at)
        self._create_channel_records_from_incomplete_browse_files()
        self._mark_new_titles_as_outdated(self.newest_browse_file().datums())
        self.upsert_source(self.source_name())
