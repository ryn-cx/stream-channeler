import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import override

from loguru import logger
from naphki.video_episodes import models as video_episodes_models
from naphki.video_programs import models as video_programs_models

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.NHKWorld.files import FileMixin, NewVideoEpisodes
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    PluginSearchResult,
    PluginSearchResults,
    URLImportResult,
)


class NHKWorld(FileMixin, register=True):
    _VERSION = "0.0.1"

    @override
    def initialize_source(self) -> None:
        if not self.has_source:
            latest_feed_file = self.latest_new_video_episodes_file()
            self.source = self._upsert_source(latest_feed_file.data_timestamp)

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Show]\n"
            "> `https://www3.nhk.or.jp/nhkworld/en/shows/japanologyplus/`\n\n"
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
        show_file = self.video_program_file(show_key)
        self.raise_invalid_url_if_no_content(show_file, url)

    def _import_show(self, show_key: str) -> Show:
        if show := self._preload_show(show_key=show_key).one_or_none():
            return show

        _cache = self._download_show_files(show_key)
        return self._upsert_show(self.source, show_key=show_key)

    @override
    def update_source(self, source: Source) -> None:
        latest_feed_file = self.latest_new_video_episodes_file()
        new_feed_file = self.new_video_episodes_file(latest_feed_file.data_timestamp)
        new_feed_file.download_if_outdated(source.update_at)
        self._process_new_episodes_files(source)
        self._upsert_source(new_feed_file.data_timestamp)

    def _process_new_episodes_files(self, source: Source) -> None:
        _cache = self._preload_sources().all()

        new_files = self.get_new_files(
            source.data_timestamp,
            NewVideoEpisodes,
            self.new_video_episodes_file,
        )
        for feed_file in new_files:
            logger.info(
                "Processing new episodes file: {}",
                feed_file.database_record.key,
            )
            for item in feed_file.items():
                show_id = item.video_program.id
                if show := Show.get_from_memory(self.session, source, show_id):
                    logger.info("Matched show: {}", show.name or show_id)
                    show.set_update_at(item.video.published_at)

    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    @classmethod
    @override
    def _url_regex(cls) -> str:
        # Example URLs:
        #   https://www3.nhk.or.jp/nhkworld/en/shows/100years-midosuji/
        return (
            cls._domain_regex()
            + r"\/nhkworld\/en\/shows\/"
            # Need to differentiate show URLs and episode URLs
            # Episode URL: https://www3.nhk.or.jp/nhkworld/en/shows/5001461/
            + r"(?P<show_key>(?=[a-z0-9_-]*[a-z_-])[a-z0-9_-]+)\/?(?:$|[?#])"
        )

    def _get_image_url(
        self,
        images: Sequence[
            video_programs_models.PortraitItem
            | video_programs_models.LandscapeItem
            | video_episodes_models.Image
        ],
    ) -> str:
        largest = max(images, key=lambda image: image.width)
        return self.build_url(largest.url)

    def _upsert_source(self, data_timestamp: datetime) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name="NHK World",
            # TODO: Don't hardcode the favicon URL
            favicon_url=self.build_url("nhkworld/common/site_images/nw_webapp.ico"),
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        program = self.video_program_file(show_key).parsed()
        show = Show(
            key=program.id,
            name=program.title,
            description=program.description,
            url=self.build_url(program.url),
            image_url=self._get_image_url(program.images.portrait),
            media_type="TV Show",
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_season(show, show_key)
        self._set_weekly_updates_from_episodes(show)

        return show

    def _upsert_season(self, show: Show, show_key: str) -> None:
        season_timestamp = self.season_data_timestamp(show_key, show_key)
        season = Season.get_from_memory(self.session, show, show_key)
        if (
            not season
            or season.data_timestamp != season_timestamp
            or season.deleted_at is not None
        ):
            season = Season(
                key=show_key,
                sort_order=0,
                url=show.url,
                data_timestamp=season_timestamp,
                show_id=show.id,
            ).upsert(show, season)

        self._upsert_episodes(season, show_key)
        self.soft_delete_missing_seasons(show_key)

    def _upsert_episodes(self, season: Season, show_key: str) -> None:
        episode_timestamp = self.episode_data_timestamp("", season.key, show_key)
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(show_key).items()))
        for sort_order, item in enumerate(items):
            existing_episode = Episode.get_from_memory(self.session, season, item.id)
            if (
                existing_episode
                and existing_episode.data_timestamp == episode_timestamp
                and existing_episode.deleted_at is None
            ):
                continue

            video = item.video
            Episode(
                key=item.id,
                name=item.title,
                url=self.build_url(item.url),
                description=item.description,
                image_url=self._get_image_url(item.images),
                release_date=video.published_at,
                air_date=item.first_broadcasted_at,
                duration=video.duration,
                sort_order=sort_order,
                episode_number=sort_order + 1,
                data_timestamp=episode_timestamp,
                season_id=season.id,
            ).upsert(season, existing_episode)

        self.soft_delete_missing_episodes(season.key)

    @override
    def search(self, query: str) -> PluginSearchResults:
        search_file = self.shows_search_file(query)
        minimum_timestamp = tz_datetime.now() - timedelta(days=7)
        search_file.download_if_outdated(minimum_timestamp)
        parsed = search_file.parsed()
        results = [
            PluginSearchResult(
                title=hit.field_source.title,
                url=self.build_url(hit.field_source.url),
                image_url=self.build_url(hit.field_source.thumbnail),
                media_type="TV Show",
            )
            for hit in parsed.hits.hits
        ]
        return PluginSearchResults(has_source_selection=False, results=results)
