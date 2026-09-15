# TODO: Validate
from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.update_at import staggered_monthly_update_at
from plugins.NHKWorld.base_files import NHKWorldBaseFiles
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.files import NewVideoEpisodes
from plugins.NHKWorld.utils import build_url, image_url, thumbnail_url, title_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from datetime import datetime

    from app.channels.models import Channel


# TODO: Validate
class NHKWorld(NHKWorldBaseFiles, BaseImporter, AbstractPlugin, register=False):
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

    # TODO: Validate
    @override
    def _next_plugin_update_at(self) -> datetime:
        return max(self._plugin_files_data_timestamps()) + timedelta(days=7)

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
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_feed_file = self.new_video_episodes_file(source.data_timestamp)
        new_feed_file.download_if_outdated(update_at)
        self._process_new_episodes_files(source)
        self.upsert_source(source.key)

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        return [item.id for item in self.video_programs_file().items()]

    # TODO: Validate
    def _title_urls_from_plugin_files(self) -> list[str]:
        return [
            title_url(title_key) for title_key in self._title_keys_from_plugin_files()
        ]

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        self.add_new_urls_to_channel(
            "All Titles",
            self._title_urls_from_plugin_files(),
        )
        self._feed_channel()
        self._process_new_episodes_files(self._sources[self.plugin_name()])

    # TODO: Validate
    def _process_new_episodes_files(self, source: Source) -> None:
        new_files = self._incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        )
        for feed_file in new_files:
            # Queueing the titles a file found commits, which lets go of every
            # matched. Read back per file rather than once, so that a file after
            # the first still recognises the titles already imported.
            _cache = self._preload_sources(preload_titles=True).all()
            logger.info(
                "Processing new episodes file: {}",
                feed_file.record_key,
            )
            new_title_ids: list[str] = []
            for item in feed_file.items():
                title_id = item.video_program.id
                if title := Title.get_from_memory(self.session, source, title_id):
                    logger.info("Matched title: {}", title.name or title_id)
                    title.set_update_at(item.video.published_at)
                else:
                    new_title_ids.append(title_id)

            self._queue_new_titles(new_title_ids)
            feed_file.clear_status()

    # TODO: Validate
    def _queue_new_titles(self, title_ids: list[str]) -> None:
        """Queue the titles a feed file named that are not imported yet."""
        new_title_urls: list[str] = []
        for title_id in dict.fromkeys(title_ids):
            logger.info("Queueing new title: {}", title_id)
            new_title_urls.append(title_url(title_id))

        # Queued in one call so the whole feed file costs a single commit.
        if new_title_urls:
            channel = self._feed_channel()
            add_urls_to_channel_import_queue(self.session, channel, new_title_urls)

    # TODO: Validate
    def _feed_channel(self) -> Channel:
        return self.get_or_create_channel(
            self.plugin_name(),
            self._channel_description("All Titles"),
        )

    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + TITLE_URL_REGEX, url):
            title_key = match.group("title_key")
            video_program_file = self.video_program_file(title_key)
            self.raise_invalid_url_if_no_content(video_program_file, url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            program = self.video_program_file(title_key).parsed()
            title = Title(
                key=program.id,
                name=program.title,
                description=program.description,
                url=build_url(program.url),
                image_url=image_url(program.images.portrait),
                thumbnail_url=thumbnail_url(program.images.portrait),
                media_type="Series",
                data_timestamp=self._title_files_data_timestamp(title_key),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(
                    title_key,
                    min(self._title_files_data_timestamps(title_key)),
                ),
            )

        self._upsert_season(title, title_key, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return title

    # TODO: Validate
    def _upsert_season(
        self,
        title: Title,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, title, title_key)
        if self._season_is_outdated(season, title_key, force=force):
            season = Season(
                key=title_key,
                season_number=1,
                sort_order=0,
                data_timestamp=self._season_files_data_timestamp(title_key, title_key),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)

        self._upsert_episodes(season, title_key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(title_key).items()))
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            episode = Episode.get_from_memory(self.session, season, item.id)
            if self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                episode = Episode(
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
                ).upsert(season, episode)
                episode.set_update_at(None)
