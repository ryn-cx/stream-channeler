# TODO: Validate
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, override
from uuid import UUID

from loguru import logger
from sqlmodel import col, select

from app.channels.models import Channel, ChannelQueue, ChannelSourceFilter, URLStatus
from app.channels.service import add_urls_to_channel_import_queue
from app.models import Visibility
from app.plugins.models import Plugin
from app.shows.models import Show
from app.users.service import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.AdultSwim.constants import FREE, SUBSCRIPTION
from plugins.AdultSwim.files import ShowsPage
from plugins.AdultSwim.upsert import UpsertMixin
from plugins.utils.base_plugin.files import (
    COMPLETED_STATUS,
    EXTRA_STATUS_FIELD,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

CHANNEL_DESCRIPTION_FILES = {
    SUBSCRIPTION: "subscription_channel_description.md",
    FREE: "free_channel_description.md",
}


# TODO: Validate
class UpdateMixin(UpsertMixin, register=False):
    # TODO: Validate
    @override
    def initialize_database(self) -> None:
        super().initialize_database()
        if self.plugin.update_at is None:
            self.plugin.update_at = tz_datetime.now()

    # TODO: Validate
    @override
    def update_plugin(self, plugin: Plugin) -> None:
        logger.info("Checking Adult Swim for new shows")
        self.shows_file(tz_datetime.now()).download_if_outdated()
        self._process_new_shows_files()
        self._exclude_subscription_from_free_channel()
        plugin.update_at = tz_datetime.now() + self._next_update_interval()

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
    def _process_new_shows_files(self) -> None:
        queued_urls = self._queued_urls()
        for shows_page in self.get_incomplete_files(ShowsPage, self.shows_file):
            _cache = self._preload_sources(preload_shows=True).all()
            logger.info("Processing shows file: {}", shows_page.database_record.key)
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
                show_url = self.show_url(show_key)
                if show_url in queued_urls:
                    continue
                logger.info("Queueing new show: {}", show_key)
                queued_urls.add(show_url)
                new_show_urls.append(show_url)

            if new_show_urls:
                for channel in self._channels():
                    add_urls_to_channel_import_queue(
                        self.session,
                        channel,
                        new_show_urls,
                    )

            shows_page.database_record.extra = {EXTRA_STATUS_FIELD: COMPLETED_STATUS}

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
        plugin_user = get_or_create_plugin_user(session=self.session)
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == plugin_user.id)
            .where(Channel.name == name),
        ).first()
        if channel:
            return channel

        channel = Channel(
            name=name,
            description=(
                Path(__file__).parent / CHANNEL_DESCRIPTION_FILES[name]
            ).read_text(encoding="utf-8"),
            visibility=Visibility.public,
            anonymous=False,
            user_id=plugin_user.id,
        )
        self.session.add(channel)
        self.session.commit()
        return channel
