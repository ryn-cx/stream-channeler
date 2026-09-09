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
from app.sources.models import Source
from app.titles.models import Title
from plugins.AdultSwim.base_files import AdultSwimBaseFiles
from plugins.AdultSwim.constants import CHANNEL_DESCRIPTION_FILES, FREE, SUBSCRIPTION
from plugins.AdultSwim.utils import title_url
from plugins.utils.constants import INCOMPLETE_STATUS

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from app.channels.models import Channel


# TODO: Validate
class AdultSwimShared(AdultSwimBaseFiles):
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
    def _upsert_source(self, source_key: str) -> Source:
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self._link_to_tmdb(),
            data_timestamp=self.titles_file().data_timestamp(),
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
    def _process_new_titles(self) -> None:
        titles_page = self.titles_file()
        if titles_page.record_status != INCOMPLETE_STATUS:
            return

        queued_urls = self._queued_urls()
        _cache = self._preload_sources(preload_titles=True).all()
        new_title_urls: list[str] = []
        for listed_title in titles_page.parsed().shows:
            title_key = listed_title.slug
            if title_key is None:
                continue
            if any(
                Title.get_from_memory(self.session, source, title_key)
                for source in self._sources.values()
            ):
                continue
            listed_title_url = title_url(title_key)
            if listed_title_url in queued_urls:
                continue
            logger.info("Queueing new title: {}", title_key)
            queued_urls.add(listed_title_url)
            new_title_urls.append(listed_title_url)

        if new_title_urls:
            for channel in self._channels():
                add_urls_to_channel_import_queue(self.session, channel, new_title_urls)

        titles_page.clear_status()

    # TODO: Validate
    def _exclude_subscription_from_free_channel(self) -> None:
        channel = self._channel(FREE)
        subscription_titles = self._subscription_titles_by_title()
        for channel_title in channel.titles:
            if channel_title.is_whitelist:
                continue
            excluded = {
                source_filter.title_id for source_filter in channel_title.source_filters
            }
            for title_id in (
                subscription_titles[channel_title.canonical_title_id] - excluded
            ):
                logger.info("Excluding the subscription title from {}", FREE)
                channel_title.source_filters.append(
                    ChannelSourceFilter(
                        channel_title_id=channel_title.id,
                        title_id=title_id,
                    ),
                )
        self.session.commit()

    # TODO: Validate
    def _subscription_titles_by_title(self) -> dict[UUID, set[UUID]]:
        by_title: dict[UUID, set[UUID]] = defaultdict(set)
        for title in self._sources[SUBSCRIPTION].titles:
            if title.deleted_at is not None:
                continue
            for title_id in title.canonical_title_ids or [title.id]:
                by_title[title_id].add(title.id)
        return by_title

    # TODO: Validate
    def _channels(self) -> Sequence[Channel]:
        return [self._channel(name) for name in CHANNEL_DESCRIPTION_FILES]

    # TODO: Validate
    def _channel(self, name: str) -> Channel:
        return self.get_or_create_channel(
            name,
            (Path(__file__).parent / CHANNEL_DESCRIPTION_FILES[name]).read_text(
                encoding="utf-8",
            ),
        )
