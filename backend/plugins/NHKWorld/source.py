# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import override

from loguru import logger
from sqlmodel import select

from app.channels.models import Channel
from app.channels.service import add_urls_to_channel_import_queue
from app.models import Visibility
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from plugins.NHKWorld.files import FileMixin, NewVideoEpisodes
from plugins.utils.base_plugin.files import (
    COMPLETED_STATUS,
    EXTRA_STATUS_FIELD,
)


# TODO: Validate
class SourceMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def update_source(self, source: Source) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_feed_file = self.new_video_episodes_file(source.data_timestamp)
        new_feed_file.download_if_outdated(source.update_at)
        self._process_new_episodes_files(source)
        self._upsert_source()

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
            feed_file.database_record.extra = {EXTRA_STATUS_FIELD: COMPLETED_STATUS}

    # TODO: Validate
    def _queue_new_shows(self, show_ids: list[str]) -> None:
        """Queue the shows a feed file named that are not imported yet."""
        new_show_urls: list[str] = []
        for show_id in dict.fromkeys(show_ids):
            logger.info("Queueing new show: {}", show_id)
            new_show_urls.append(self.show_url(show_id))

        # Queued in one call so the whole feed file costs a single commit.
        if new_show_urls:
            add_urls_to_channel_import_queue(
                self.session,
                self._feed_channel(),
                new_show_urls,
            )

    # TODO: Validate
    def _feed_channel(self) -> Channel:
        """Return the plugin owned channel every NHK World show is queued into.

        The new episodes feed only reaches back so far, so a show drops off it
        once nothing new has aired and the channel is what keeps hold of the
        whole library. It is created the first time a show is found rather than
        by hand.
        """
        plugin_user = get_or_create_plugin_user(session=self.session)
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == plugin_user.id)
            .where(Channel.name == self.plugin_name()),
        ).first()
        if channel:
            return channel

        channel = Channel(
            name=self.plugin_name(),
            description=(Path(__file__).parent / "channel_description.md").read_text(
                encoding="utf-8",
            ),
            visibility=Visibility.public,
            anonymous=False,
            user_id=plugin_user.id,
        )
        self.session.add(channel)
        self.session.commit()
        return channel

    # TODO: Validate
    def _upsert_source(self) -> Source:
        if not (latest_feed_file := self.latest_new_video_episodes_file()):
            latest_feed_file = self._initial_file(NewVideoEpisodes)
            latest_feed_file.download_if_outdated()
        data_timestamp = latest_feed_file.data_timestamp
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            update_at=data_timestamp + timedelta(days=1),
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source, self._source_files())
