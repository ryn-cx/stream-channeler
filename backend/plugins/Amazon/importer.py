# TODO: Validate
"""Writing what Prime Video says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.titles.models import Title
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Amazon.shared import (
    AMAZON_URL_REGEX,
    PRIME_VIDEO_URL_REGEX,
    SHARE_URL_REGEX,
    AmazonShared,
)
from plugins.Amazon.utils import detail_url, parse_date
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class AmazonImporter(AmazonShared, BaseImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            # Must be listed first: a share link's path is also a detail path, and
            # only this one carries the id in the query rather than the path.
            SHARE_URL_REGEX,
            PRIME_VIDEO_URL_REGEX,
            AMAZON_URL_REGEX,
        )

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        title_key: str | None
        if match := re.match(domain_regex + SHARE_URL_REGEX, url):
            # Amazon answers a share link by pointing at the page its own ids key,
            # so the id is read off where the link lands rather than out of the link.
            title_key = self.title_key_from_share_key(
                match.group("watch_amazon_title_key"),
            )
        elif match := re.match(domain_regex + PRIME_VIDEO_URL_REGEX, url):
            title_key = match.group("prime_video_title_key")
        elif match := re.match(domain_regex + AMAZON_URL_REGEX, url):
            title_key = match.group("amazon_title_key")
        else:
            title_key = None

        if title_key is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        detail_file = self.detail_file(title_key)
        self.raise_if_invalid_file(detail_file, url)
        if message := detail_file.unavailable_message():
            msg = f"{message}: {url}"
            raise InvalidURLError(msg)

        return MediaInfo(self.title_key_from_title_key(title_key))

    # TODO: Validate
    @override  # Writes the title into every source it can be watched through.
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.extract_media_info(url)
        if titles := self._preload_title(media_info.title_key).all():
            return [
                result
                for title in titles
                for result in self._import_results(title, media_info)
            ]

        results: list[URLImportResult] = []
        for source in self.title_sources(media_info.title_key):
            title = self.upsert_title(source, media_info.title_key)
            results += self._import_results(title, media_info)
        return results

    # TODO: Validate
    def _title_url(self, title_key: str) -> str:
        return detail_url(self.detail_file(title_key).compact_key())

    # TODO: Validate
    def _tmdb_lookup_info(
        self,
        title_key: str,
        media_type: TMDBMediaType,
    ) -> list[TMDBLookupInfo]:
        page = self.detail_file(title_key)
        page.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return [
            TMDBLookupInfo(page.series_title(), media_type, page.release_year()),
        ]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.detail_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect changes to the season and new episodes of it.
            self.detail_file(season_key),
            # Required to detect a season being taken off the title.
            self.detail_file(title_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return [self.detail_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [season.key for season in self._season_entries(title_key)]


# TODO: Validate
class AmazonSeries(AmazonImporter):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(title_key, TMDBMediaType.tv)

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
            episode.key
            for season_key in season_keys
            for episode in self.detail_file(season_key).episodes()
        ]

    # TODO: Validate
    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        page = self.detail_file(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self.title_data_timestamps(title_key)
            data_timestamp = data_timestamps[0]
            new_title = Title(
                key=title_key,
                name=page.series_title(),
                description=page.synopsis(),
                media_type="Series",
                url=self._title_url(title_key),
                image_url=page.image_url(),
                thumbnail_url=page.image_url(),
                year=page.release_year(),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(data_timestamp + timedelta(days=7), data_timestamps)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)
        self._set_weekly_updates_from_episodes(title, update_title=False)
        self.link_title_to_tmdb(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_entry in enumerate(self._season_entries(title.key)):
            season_key = season_entry.key
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                new_season = Season(
                    key=season_key,
                    name=season_entry.name,
                    season_number=season_entry.season_number,
                    sort_order=sort_order,
                    url=detail_url(season_key),
                    data_timestamp=data_timestamps[0],
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, item in enumerate(self.detail_file(season.key).episodes()):
            episode = Episode.get_from_memory(self.session, season, item.key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                item.key,
                season.key,
                title_key,
            )
            new_episode = Episode(
                key=item.key,
                watch_identifier=watch_identifier(self.plugin_name(), item.key),
                name=item.title,
                episode_number=item.episode_number,
                url=detail_url(item.compact_key),
                description=item.synopsis,
                image_url=item.image_url,
                thumbnail_url=item.image_url,
                duration=item.duration,
                air_date=parse_date(item.release_date),
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class AmazonMovie(AmazonImporter):
    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        return self._tmdb_lookup_info(title_key, TMDBMediaType.movie)

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        # A film is the only episode of the only season of itself.
        return list(season_keys)

    # TODO: Validate
    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        page = self.detail_file(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self.title_data_timestamps(title_key)
            data_timestamp = data_timestamps[0]
            new_title = Title(
                key=title_key,
                name=page.title(),
                description=page.synopsis(),
                media_type="Movie",
                url=self._title_url(title_key),
                image_url=page.image_url(),
                thumbnail_url=page.image_url(),
                year=page.release_year(),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_season(title, force=force)
        self._soft_delete_missing(title_key)
        self._set_weekly_updates_from_episodes(title, update_title=False)
        self.link_title_to_tmdb(title)

        return title

    # TODO: Validate
    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season = Season.get_from_memory(self.session, title, title.key)
        if self._season_is_outdated(season, title.key, force=force):
            data_timestamps = self.season_data_timestamps(title.key, title.key)
            new_season = Season(
                key=title.key,
                season_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                title_id=title.id,
            )
            season = new_season.upsert(title, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episode(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if not self._episode_is_outdated(
            episode,
            season.key,
            title_key,
            force=force,
        ):
            return

        page = self.detail_file(title_key)
        data_timestamps = self.episode_data_timestamps(title_key, season.key, title_key)
        new_episode = Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=page.title(),
            description=page.synopsis(),
            url=self._title_url(title_key),
            image_url=page.image_url(),
            thumbnail_url=page.image_url(),
            duration=page.duration(),
            episode_number=0,
            sort_order=0,
            air_date=parse_date(page.release_date()),
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
