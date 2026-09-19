# TODO: Validate
from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger

from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from plugins.NHKWorld.base_files import NHKWorldBaseFiles
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.files import NewVideoEpisodes
from plugins.NHKWorld.utils import build_url, image_url, thumbnail_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from datetime import datetime

    from naphki.video_episodes.models import Item


class NHKWorldChannels(NHKWorldBaseFiles, BaseImporter, ABC):
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        program = self.video_program_file(title.key).parsed()
        channel_keys = ["All Titles"]
        channel_keys.extend(category.name for category in program.categories)
        for channel_key in channel_keys:
            self.add_new_urls_to_channel(channel_key, [title.url])

    @override
    def create_initial_channel_records(self) -> None:
        self.video_programs_file().download_if_outdated()
        title_keys = [item.id for item in self.video_programs_file().items()]
        self._add_titles_to_all_titles_channel(title_keys)

    def _create_channel_records_from_incomplete_feed_files(self) -> None:
        for feed_file in self._incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        ):
            title_keys = [item.video_program.id for item in feed_file.items()]
            self._add_titles_to_all_titles_channel(title_keys)
            feed_file.clear_status()


# TODO: Validate
class NHKWorldUpsert(NHKWorldChannels, ABC):
    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        program = self.video_program_file(title_key).parsed()
        upserted_title = Title(
            key=program.id,
            name=program.title,
            description=program.description,
            url=build_url(program.url),
            image_url=image_url(program.images.portrait),
            thumbnail_url=thumbnail_url(program.images.portrait),
            media_type=MediaType.series,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(category.name for category in program.categories)

        self._upsert_season(upserted_title, title_key)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
    ) -> None:
        existing_season = Season.get_from_memory(self.session, title, title_key)
        upserted_season = Season(
            key=title_key,
            season_number=1,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(title_key, title_key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episodes(upserted_season, title_key)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(title_key).items()))
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            existing_episode = Episode.get_from_memory(self.session, season, item.id)
            Episode(
                key=item.id,
                watch_identifier=watch_identifier(self.plugin_name(), item.id),
                name=item.title,
                url=build_url(item.url),
                description=item.description,
                image_url=image_url(item.images),
                thumbnail_url=thumbnail_url(item.images),
                air_date=item.first_broadcasted_at,
                duration=item.video.duration,
                sort_order=sort_order,
                episode_number=sort_order + 1,
                data_timestamp=self._episode_files_data_timestamp(
                    item.id,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class NHKWorld(NHKWorldUpsert, AbstractPlugin, register=True):
    # TODO: Add support for single episodes
    # TODO: Don't hardcode the favicon URL
    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def _next_source_update_at(self) -> datetime:
        return self._source_files_data_timestamp() + timedelta(days=1)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        latest_feed_file = self.latest_new_video_episodes_file()
        feed_datetime = (
            latest_feed_file.record_data_timestamp
            if latest_feed_file
            else tz_datetime.now()
        )
        feed_file = self.new_video_episodes_file(feed_datetime)
        feed_file.download_if_outdated(update_at)
        self._create_channel_records_from_incomplete_feed_files()
        self._mark_new_titles_as_outdated(source, feed_file.items())
        self.upsert_source(source.key)

    # TODO: Validate
    def _mark_new_titles_as_outdated(self, source: Source, items: list[Item]) -> None:
        _cache = self._preload_sources(preload_titles=True).all()
        for item in items:
            title_id = item.video_program.id
            if title := Title.get_from_memory(self.session, source, title_id):
                logger.info("Matched title: {}", title.name or title_id)
                title.set_update_at(item.video.published_at)

    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            video_program_file = self.video_program_file(title_key)
            self.raise_invalid_url_if_no_content(video_program_file, url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
