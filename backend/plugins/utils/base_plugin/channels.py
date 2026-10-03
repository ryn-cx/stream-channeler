from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import suppress
from datetime import datetime, timedelta
from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy import String, cast
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, func, select

from app.channels.models import Channel, ChannelQueue, ChannelTitle
from app.channels.service.import_queue import (
    add_missing_urls_to_channel_import_queue,
)
from app.channels.service.ordering import order_preset_options
from app.models import Visibility
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.users.service.accounts import get_or_create_automatic_channel_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.url import BaseURLMixin

if TYPE_CHECKING:
    import uuid
    from collections.abc import Collection, Iterable, Sequence

    from app.plugins.models import Plugin


# TODO: Validate
class BaseChannelMixin(BaseURLMixin, ABC):
    session: Session
    plugin: Plugin

    @classmethod
    @abstractmethod
    def source_name(cls) -> str: ...

    @cached_property
    def automatic_channel_user(self) -> User:
        return get_or_create_automatic_channel_user(self.session, self.source_name())

    # TODO: Validate
    def add_title_to_plugin_channels(self, title: Title) -> None:  # noqa: ARG002
        return

    # TODO: Validate
    def _get_or_create_channels(self, channel_keys: Collection[str]) -> list[Channel]:
        channel_keys_by_name = {
            self._channel_name(channel_key): channel_key for channel_key in channel_keys
        }
        existing_channels = {
            channel.name: channel
            for channel in self.session.exec(
                select(Channel).where(
                    Channel.user_id == self.automatic_channel_user.id,
                    col(Channel.name).in_(channel_keys_by_name),
                ),
            ).all()
        }
        channels = [
            existing_channels.get(channel_name)
            or self._create_channel(
                channel_name,
                self._channel_description(channel_key),
            )
            for channel_name, channel_key in channel_keys_by_name.items()
        ]
        if len(existing_channels) < len(channels):
            self.session.flush()
        return channels

    # TODO: Validate
    def _create_channel(self, channel_name: str, channel_description: str) -> Channel:
        channel = Channel(
            name=channel_name,
            description=channel_description,
            visibility=Visibility.public,
            anonymous=False,
            # Automatically generated channels should always appear after user
            # created channels.
            score=-1,
            # Roll The Dice is the default order because it is fast and changes the
            # episode order when refreshed.
            default_order=order_preset_options(self.session, "Roll The Dice"),
            update_at=tz_datetime.now() + timedelta(days=1),
            user_id=self.automatic_channel_user.id,
        )
        self.session.add(channel)
        return channel

    def _channel_name(self, topic_prefix: str) -> str:
        """Return the channel name for an automatically generated channel."""
        return f"{topic_prefix} on {self.source_name()}"

    def _channel_description(self, topic_prefix: str) -> str:
        """Return the channel description for an automatically generated channel."""
        # When making an "All Titles" channel "All" is manually appended to the topic
        # but is redundant in the description.
        return (
            f"All {topic_prefix.removeprefix('All ')} titles on {self.source_name()}.\n\n"
            "This is an automatically generated channel based on the titles that have been imported by all of Stream Channeler's users."
        )

    # TODO: Validate
    def _titles_by_url(self, urls: set[str]) -> dict[str, list[Title]]:
        title_keys_by_url = self._title_keys_by_url(urls)
        titles = self.session.exec(
            select(Title)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(Title.key)
                == func.any(cast(list(set(title_keys_by_url.values())), ARRAY(String))),
            )
            .options(selectinload(Title.tmdb_title_links)),  # type: ignore[arg-type]
        ).all()

        titles_by_key: dict[str, list[Title]] = {}
        for title in titles:
            titles_by_key.setdefault(title.key, []).append(title)
        return {
            url: titles_by_key[title_key]
            for url, title_key in title_keys_by_url.items()
            if title_key in titles_by_key
        }

    # TODO: Validate
    @classmethod
    def title_url(cls, title_key: str) -> str:
        raise NotImplementedError

    # TODO: Validate
    def _title_keys_by_url(self, urls: Collection[str]) -> dict[str, str]:
        title_keys_by_url: dict[str, str] = {}
        for url in urls:
            with suppress(InvalidURLError):
                title_keys_by_url[url] = self.title_key_from_url(url)
        return title_keys_by_url

    # TODO: Validate
    def add_new_urls_to_channel(
        self,
        channel_key: str,
        urls: Collection[str],
    ) -> None:
        self.add_new_urls_to_channels([channel_key], urls)

    # TODO: Validate
    def add_new_urls_to_channels(
        self,
        channel_keys: Collection[str],
        urls: Collection[str],
    ) -> None:
        if not urls or not channel_keys:
            return

        for channel in self._get_or_create_channels(channel_keys):
            add_missing_urls_to_channel_import_queue(self.session, channel, list(urls))
        self.session.commit()

    # TODO: Validate
    def replace_list_channels(
        self,
        urls_by_channel_key: dict[str, list[str]],
        data_timestamp: datetime,
    ) -> None:
        channels = self._get_or_create_channels(urls_by_channel_key)
        for (channel_key, urls), channel in zip(
            urls_by_channel_key.items(),
            channels,
            strict=True,
        ):
            if channel.data_timestamp and channel.data_timestamp >= data_timestamp:
                continue
            channel.data_timestamp = data_timestamp
            self._replace_list_channel(channel_key, channel, urls)

    # TODO: Validate
    def _replace_list_channel(
        self,
        channel_key: str,
        channel: Channel,
        urls: Collection[str],
    ) -> None:
        titles_by_url = self._titles_by_url(set(urls))
        imported_title_ids_by_tmdb_title_id = {
            tmdb_title_id: title.id
            for titles in titles_by_url.values()
            for title in titles
            if title.deleted_at is None
            for tmdb_title_id in self._tmdb_title_ids([title])
        }

        existing_tmdb_title_ids: set[uuid.UUID] = set()
        for channel_title in self.session.exec(
            select(ChannelTitle).where(ChannelTitle.channel_id == channel.id),
        ).all():
            if channel_title.tmdb_title_id in imported_title_ids_by_tmdb_title_id:
                channel_title.is_blacklist_only = False
                existing_tmdb_title_ids.add(channel_title.tmdb_title_id)
            else:
                self.session.delete(channel_title)
        self.session.add_all(
            ChannelTitle(
                channel_id=channel.id,
                tmdb_title_id=tmdb_title_id,
                imported_title_id=imported_title_id,
                is_whitelist=False,
                is_blacklist_only=False,
            )
            for tmdb_title_id, imported_title_id in (
                imported_title_ids_by_tmdb_title_id.items()
            )
            if tmdb_title_id not in existing_tmdb_title_ids
        )

        for queue_entry in self.session.exec(
            select(ChannelQueue).where(
                ChannelQueue.channel_id == channel.id,
                col(ChannelQueue.url).not_in(urls),
            ),
        ).all():
            self.session.delete(queue_entry)
        self.session.flush()

        self.add_new_urls_to_channel(
            channel_key,
            [url for url in urls if url not in titles_by_url],
        )

    # TODO: Validate
    @staticmethod
    def _tmdb_title_ids(titles: Sequence[Title]) -> set[uuid.UUID]:
        return {
            tmdb_title_id
            for title in titles
            for tmdb_title_id in (title.tmdb_title_ids or [title.id])
        }

    def _deleted_titles_in_queue(
        self,
        queue_entries: Sequence[ChannelQueue],
    ) -> list[ChannelQueue]:
        titles_by_queued_url = self._titles_by_url(
            {queue_entry.url for queue_entry in queue_entries},
        )

        tmdb_record_ids_by_queued_url = {
            queued_url: {
                tmdb_title_id
                for title in queued_url_titles
                for tmdb_title_id in title.tmdb_title_ids
            }
            for queued_url, queued_url_titles in titles_by_queued_url.items()
            if all(title.deleted_at is not None for title in queued_url_titles)
        }
        active_tmdb_title_ids = self._active_tmdb_title_ids(
            {
                tmdb_title_id
                for tmdb_title_ids in tmdb_record_ids_by_queued_url.values()
                for tmdb_title_id in tmdb_title_ids
            },
        )
        deleted_urls_in_queue = {
            queued_url
            for queued_url, tmdb_title_ids in tmdb_record_ids_by_queued_url.items()
            if not tmdb_title_ids & active_tmdb_title_ids
        }
        return [
            queue_entry
            for queue_entry in queue_entries
            if queue_entry.url in deleted_urls_in_queue
        ]

    def _active_tmdb_title_ids(
        self,
        tmdb_title_ids: set[uuid.UUID],
    ) -> set[uuid.UUID]:
        active_title_ids = self.session.exec(
            select(Title.id)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(Title.id).in_(tmdb_title_ids),
                col(Title.deleted_at).is_(None),
            ),
        ).all()
        active_titles_tmdb_record_ids = self.session.exec(
            select(TitleTmdbTitle.tmdb_title_id)
            .join(Title, col(Title.id) == col(TitleTmdbTitle.title_id))
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(TitleTmdbTitle.tmdb_title_id).in_(tmdb_title_ids),
                col(Title.deleted_at).is_(None),
            ),
        ).all()
        return set(active_title_ids) | set(active_titles_tmdb_record_ids)

    # TODO: Validate
    def add_title_to_channel(self, channel_key: str, title: Title) -> None:
        channel = self._get_or_create_channels([channel_key])[0]
        tmdb_title_ids = self._tmdb_title_ids([title])
        existing_tmdb_title_ids = set(
            self.session.exec(
                select(ChannelTitle.tmdb_title_id).where(
                    ChannelTitle.channel_id == channel.id,
                    col(ChannelTitle.tmdb_title_id).in_(tmdb_title_ids),
                ),
            ).all(),
        )
        self.session.add_all(
            ChannelTitle(
                channel_id=channel.id,
                tmdb_title_id=tmdb_title_id,
                imported_title_id=title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            )
            for tmdb_title_id in tmdb_title_ids - existing_tmdb_title_ids
        )
        self.session.flush()

    # TODO: Validate
    def remove_title_from_plugin_channels(self, title: Title) -> None:
        tmdb_title_ids = self._tmdb_title_ids([title])
        removable_tmdb_title_ids = tmdb_title_ids - self._active_tmdb_title_ids(
            tmdb_title_ids,
        )
        channel_titles = self.session.exec(
            select(ChannelTitle)
            .join(Channel, col(Channel.id) == col(ChannelTitle.channel_id))
            .where(
                Channel.user_id == self.automatic_channel_user.id,
                col(ChannelTitle.tmdb_title_id).in_(removable_tmdb_title_ids),
            ),
        ).all()
        for channel_title in channel_titles:
            self.session.delete(channel_title)

        if title.url:
            queue_entries = self.session.exec(
                select(ChannelQueue)
                .join(Channel, col(Channel.id) == col(ChannelQueue.channel_id))
                .where(
                    Channel.user_id == self.automatic_channel_user.id,
                    ChannelQueue.url == title.url,
                ),
            ).all()
            for queue_entry in self._deleted_titles_in_queue(queue_entries):
                self.session.delete(queue_entry)
        self.session.flush()

    # TODO: Validate
    def set_title_tag_channels(
        self,
        title: Title,
        channel_keys: Collection[str],
    ) -> None:
        channels = self._get_or_create_channels(channel_keys)
        for channel in channels:
            channel.is_tag_based = True
        channel_ids = {channel.id for channel in channels}
        tmdb_title_ids = self._tmdb_title_ids([title])

        tag_channel_titles = self.session.exec(
            select(ChannelTitle)
            .join(Channel, col(Channel.id) == col(ChannelTitle.channel_id))
            .where(
                Channel.user_id == self.automatic_channel_user.id,
                col(Channel.is_tag_based).is_(True),
                col(ChannelTitle.tmdb_title_id).in_(tmdb_title_ids),
            ),
        ).all()
        existing_channel_titles: set[tuple[uuid.UUID, uuid.UUID]] = set()
        for channel_title in tag_channel_titles:
            if channel_title.channel_id in channel_ids:
                channel_title.is_blacklist_only = False
                existing_channel_titles.add(
                    (channel_title.channel_id, channel_title.tmdb_title_id),
                )
            else:
                self.session.delete(channel_title)

        stale_queue_entries = self.session.exec(
            select(ChannelQueue)
            .join(Channel, col(Channel.id) == col(ChannelQueue.channel_id))
            .where(
                Channel.user_id == self.automatic_channel_user.id,
                col(Channel.is_tag_based).is_(True),
                col(ChannelQueue.channel_id).not_in(channel_ids),
                ChannelQueue.url == title.url,
            ),
        ).all()
        for queue_entry in stale_queue_entries:
            self.session.delete(queue_entry)

        self.session.add_all(
            ChannelTitle(
                channel_id=channel_id,
                tmdb_title_id=tmdb_title_id,
                imported_title_id=title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            )
            for channel_id in channel_ids
            for tmdb_title_id in tmdb_title_ids
            if (channel_id, tmdb_title_id) not in existing_channel_titles
        )
        self.session.flush()


# TODO: Validate
class BaseUpserterChannelMixin(BaseChannelMixin, ABC):
    # TODO: Validate
    def add_title_to_channels(self, title: Title) -> None:
        if title.deleted_at is not None:
            self.remove_title_from_plugin_channels(title)
            return
        self.add_title_to_plugin_channels(title)


# TODO: Validate
class BasePluginChannelMixin(BaseChannelMixin, ABC):
    # TODO: Validate
    def _add_titles_to_all_titles_channel(self, title_keys: Iterable[str]) -> None:
        urls = [self.title_url(title_key) for title_key in title_keys]
        self.add_new_urls_to_channel("All Titles", urls)

    # TODO: Validate
    def _has_title_key(self, url: str) -> bool:
        try:
            self.title_key_from_url(url)
        except InvalidURLError:
            return False
        return True

    def _remove_queue_entries_with_deleted_titles(self, channel: Channel) -> None:
        urls_in_queue = self.session.exec(
            select(ChannelQueue)
            .join(Channel, col(Channel.id) == col(ChannelQueue.channel_id))
            .join(User, col(User.id) == col(Channel.user_id))
            .where(
                ChannelQueue.channel_id == channel.id,
                is_plugin_user(User.email),
            ),
        ).all()

        for queue_entry in self._deleted_titles_in_queue(urls_in_queue):
            self.session.delete(queue_entry)
