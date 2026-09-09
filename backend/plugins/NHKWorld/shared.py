# TODO: Validate
"""What the plugin, its importers and its initializer all read NHK World by."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.NHKWorld.base_files import NHKWorldBaseFiles
from plugins.NHKWorld.files import NewVideoEpisodes
from plugins.NHKWorld.utils import title_url

if TYPE_CHECKING:
    from app.channels.models import Channel


# TODO: Validate
class NHKWorldShared(NHKWorldBaseFiles):
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
    def upsert_source(self, source_key: str) -> Source:
        if not (latest_feed_file := self.latest_new_video_episodes_file()):
            latest_feed_file = self.new_video_episodes_file(tz_datetime.now())
        data_timestamp = latest_feed_file.data_timestamp()
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(data_timestamp + timedelta(days=1))
        return source

    # TODO: Validate
    def _process_new_episodes_files(self, source: Source) -> None:
        new_files = self._incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        )
        for feed_file in new_files:
            # Queueing the titles a file found commits, which lets go of every
            # title read for it, and a title nothing holds is not in memory to be
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
        """Return the plugin owned channel every NHK World title is queued into.

        The new episodes feed only reaches back so far, so a title drops off it
        once nothing new has aired and the channel is what keeps hold of the
        whole library. It is created the first time a title is found rather than
        by hand.
        """
        return self.get_or_create_channel(
            self.plugin_name(),
            (Path(__file__).parent / "channel_description.md").read_text(
                encoding="utf-8",
            ),
        )
