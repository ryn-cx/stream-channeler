# TODO: Validate
"""What the plugin, its importers and its initializer all read NHK World by."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.shows.models import Show
from app.sources.models import Source
from plugins.NHKWorld.basic_files import BasicFiles
from plugins.NHKWorld.files import NewVideoEpisodes
from plugins.NHKWorld.utils import search_url, show_url
from plugins.utils.base_plugin.files import COMPLETED_STATUS

if TYPE_CHECKING:
    from app.channels.models import Channel

# https://www3.nhk.or.jp/nhkworld/en/shows/100years-midosuji/
# The lookahead requires a non-numeric character so this matches show slugs but
# not numeric episode URLs like https://www3.nhk.or.jp/nhkworld/en/shows/5001461/
SHOW_URL_REGEX = (
    r"\/nhkworld\/en\/shows\/(?P<show_key>(?=[a-z0-9_-]*[a-z_-])[a-z0-9_-]+)"
    r"\/?(?:$|[?#])"
)


# TODO: Validate
class NHKWorldShared(BasicFiles):
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
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        if not (latest_feed_file := self.latest_new_video_episodes_file()):
            latest_feed_file = self._initial_file(NewVideoEpisodes)
        data_timestamp = latest_feed_file.data_timestamp()
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(data_timestamp + timedelta(days=1))
        return source

    # TODO: Validate
    def _process_new_episodes_files(self, source: Source) -> None:
        new_files = self.get_incomplete_files(
            NewVideoEpisodes,
            self.new_video_episodes_file,
        )
        for feed_file in new_files:
            # Queueing the shows a file found commits, which lets go of every
            # show read for it, and a show nothing holds is not in memory to be
            # matched. Read back per file rather than once, so that a file after
            # the first still recognises the shows already imported.
            _cache = self._preload_sources(preload_shows=True).all()
            logger.info(
                "Processing new episodes file: {}",
                feed_file.database_record.key,
            )
            new_show_ids: list[str] = []
            for item in feed_file.items():
                show_id = item.video_program.id
                if show := Show.get_from_memory(self.session, source, show_id):
                    logger.info("Matched show: {}", show.name or show_id)
                    show.set_update_at(item.video.published_at)
                else:
                    new_show_ids.append(show_id)

            self._queue_new_shows(new_show_ids)
            feed_file.database_record.status = COMPLETED_STATUS

    # TODO: Validate
    def _queue_new_shows(self, show_ids: list[str]) -> None:
        """Queue the shows a feed file named that are not imported yet."""
        new_show_urls: list[str] = []
        for show_id in dict.fromkeys(show_ids):
            logger.info("Queueing new show: {}", show_id)
            new_show_urls.append(show_url(show_id))

        # Queued in one call so the whole feed file costs a single commit.
        if new_show_urls:
            channel = self._feed_channel()
            add_urls_to_channel_import_queue(self.session, channel, new_show_urls)

    # TODO: Validate
    def _feed_channel(self) -> Channel:
        """Return the plugin owned channel every NHK World show is queued into.

        The new episodes feed only reaches back so far, so a show drops off it
        once nothing new has aired and the channel is what keeps hold of the
        whole library. It is created the first time a show is found rather than
        by hand.
        """
        return self.add_urls_to_plugin_channel(
            self.plugin_name(),
            (Path(__file__).parent / "channel_description.md").read_text(
                encoding="utf-8",
            ),
        )
