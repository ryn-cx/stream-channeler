# TODO: Validate
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import ClassVar, override

from loguru import logger
from naphki.video_episodes import models as video_episodes_models
from naphki.video_programs import models as video_programs_models

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.NHKWorld.files import FileMixin, NewVideoEpisodes
from plugins.NHKWorld.handlers import NHKWorldURLHandler, ShowURLHandler
from plugins.utils.abstract_plugin import (
    PluginSearchResult,
    PluginSearchResults,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class NHKWorld(FileMixin, URLHandlerPlugin[NHKWorldURLHandler], register=True):
    _VERSION = "0.0.1"

    # TODO: Add support for single episodes
    _URL_HANDLERS: ClassVar[tuple[type[NHKWorldURLHandler], ...]] = (ShowURLHandler,)

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Show]\n"
            "> `https://www3.nhk.or.jp/nhkworld/en/shows/japanologyplus/`\n\n"
        )

    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_feed_file = self.new_video_episodes_file(source.data_timestamp)
        new_feed_file.download_if_outdated(source.update_at)
        self._process_new_episodes_files(source)
        self._upsert_source()

    def _process_new_episodes_files(self, source: Source) -> None:
        _cache = self._preload_sources(preload_shows=True).all()

        new_files = self.get_incomplete_files(
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
                else:
                    # NHK World has a small library so new shows can be imported
                    # immediately.
                    logger.info("Importing new show: {}", show_id)
                    self._download_show_files_and_children(show_id)
                    self._upsert_show(source, show_id)

            feed_file.database_record.extra = "Completed"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

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

    def _upsert_source(self) -> Source:
        if not (latest_feed_file := self.latest_new_video_episodes_file()):
            latest_feed_file = self.new_video_episodes_file(tz_datetime.now())
            latest_feed_file.download_if_outdated()
        data_timestamp = latest_feed_file.data_timestamp
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name="NHK World",
            # TODO: Don't hardcode the favicon URL
            favicon_url=self.build_url("nhkworld/common/site_images/nw_webapp.ico"),
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())

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
        ).upsert_and_set_update_at(source, existing_show, self._show_files(show_key))

        self._upsert_season(show, show_key)

        return show

    def _upsert_season(self, show: Show, show_key: str) -> None:
        if season_check := self._season_check(show, show_key, show_key):
            season_files = self._season_files(show_key, show_key)
            season = Season(
                key=show_key,
                sort_order=0,
                url=show.url,
                data_timestamp=season_check.data_timestamp,
                show_id=show.id,
            ).upsert_and_set_update_at(show, season_check.record, season_files)
        else:
            season = season_check.record

        self._upsert_episodes(season, show_key)
        self.soft_delete_missing_seasons(show_key)

    def _upsert_episodes(self, season: Season, show_key: str) -> None:
        # Episodes are listed newest to oldest.
        items = list(reversed(self.video_episodes_file(show_key).items()))
        for sort_order, item in enumerate(items):
            season.set_update_at(item.video.expired_at)

            episode_check = self._episode_check(
                item.id,
                season,
                show_key,
            )
            if not episode_check:
                continue

            video = item.video
            episode_files = self._episode_files(item.id, season.key, show_key)
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
                episode_identifier=f"NHKWorld {item.id}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert_and_set_update_at(season, episode_check.record, episode_files)

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
        return PluginSearchResults(results=results)
