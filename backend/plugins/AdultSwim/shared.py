# TODO: Validate
"""What the plugin, its importers and its initializer all read Adult Swim by."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override

from loguru import logger
from sqlmodel import col, select

from app.channels.models import ChannelQueue, ChannelSourceFilter, URLStatus
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.shows.models import Show
from app.sources.models import Source
from plugins.AdultSwim.basic_files import BasicFiles
from plugins.AdultSwim.constants import FREE, SUBSCRIPTION
from plugins.AdultSwim.utils import show_url
from plugins.utils.base_plugin.files import COMPLETED_STATUS

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from app.channels.models import Channel

EPISODE_URL_REGEX = r"\/videos\/(?P<episode_path>[a-z0-9-]+\/[a-z0-9-]+)(?:[\/?#]|$)"
SHOW_URL_REGEX = (
    r"\/(?!videos(?:$|[?#]|\/(?:$|[?#])))"
    r"(?:videos\/)?(?P<show_key>[a-z0-9-]+)\/?(?:$|[?#])"
)

CHANNEL_DESCRIPTION_FILES = {
    SUBSCRIPTION: "subscription_channel_description.md",
    FREE: "free_channel_description.md",
}


# TODO: Validate
class AdultSwimShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Adult Swim"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.adultswim.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "adultswim.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (FREE, SUBSCRIPTION)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=source_key,
            favicon_url=self.favicon_url(),
            data_timestamp=self.shows_file().data_timestamp(),
            plugin_id=self.plugin.id,
            # update_at is not used because it Plugin.update_at is used instead because
            # there are multiple sources that used the same file.
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source

    # TODO: Validate
    def _next_update_interval(self) -> timedelta:
        pending = self.session.exec(
            select(ChannelQueue.id)
            .where(
                col(ChannelQueue.channel_id).in_(
                    [channel.id for channel in self._channels()],
                ),
                col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]),
            )
            .limit(1),
        ).first()
        return timedelta(days=1) if pending else timedelta(days=30)

    # TODO: Validate
    def _queued_urls(self) -> set[str]:
        return set(
            self.session.exec(
                select(ChannelQueue.url).where(
                    col(ChannelQueue.channel_id).in_(
                        [channel.id for channel in self._channels()],
                    ),
                ),
            ).all(),
        )

    # TODO: Validate
    def _process_new_shows(self) -> None:
        shows_page = self.shows_file()
        record = shows_page.database_record
        if record.status == COMPLETED_STATUS:
            return

        queued_urls = self._queued_urls()
        _cache = self._preload_sources(preload_shows=True).all()
        new_show_urls: list[str] = []
        for listed_show in shows_page.parsed().shows:
            show_key = listed_show.slug
            if show_key is None:
                continue
            if any(
                Show.get_from_memory(self.session, source, show_key)
                for source in self._sources.values()
            ):
                continue
            listed_show_url = show_url(show_key)
            if listed_show_url in queued_urls:
                continue
            logger.info("Queueing new show: {}", show_key)
            queued_urls.add(listed_show_url)
            new_show_urls.append(listed_show_url)

        if new_show_urls:
            for channel in self._channels():
                add_urls_to_channel_import_queue(self.session, channel, new_show_urls)

        record.status = COMPLETED_STATUS

    # TODO: Validate
    def _exclude_subscription_from_free_channel(self) -> None:
        channel = self._channel(FREE)
        subscription_shows = self._subscription_shows_by_title()
        for channel_show in channel.shows:
            if channel_show.is_whitelist:
                continue
            excluded = {
                source_filter.show_id for source_filter in channel_show.source_filters
            }
            for show_id in (
                subscription_shows[channel_show.canonical_show_id] - excluded
            ):
                logger.info("Excluding the subscription show from {}", FREE)
                channel_show.source_filters.append(
                    ChannelSourceFilter(
                        channel_show_id=channel_show.id,
                        show_id=show_id,
                    ),
                )
        self.session.commit()

    # TODO: Validate
    def _subscription_shows_by_title(self) -> dict[UUID, set[UUID]]:
        by_title: dict[UUID, set[UUID]] = defaultdict(set)
        for show in self._sources[SUBSCRIPTION].shows:
            if show.deleted_at is not None:
                continue
            for title_id in show.canonical_show_ids or [show.id]:
                by_title[title_id].add(show.id)
        return by_title

    # TODO: Validate
    def _channels(self) -> Sequence[Channel]:
        return [self._channel(name) for name in CHANNEL_DESCRIPTION_FILES]

    # TODO: Validate
    def _channel(self, name: str) -> Channel:
        return self.add_urls_to_plugin_channel(
            name,
            (Path(__file__).parent / CHANNEL_DESCRIPTION_FILES[name]).read_text(
                encoding="utf-8",
            ),
        )
