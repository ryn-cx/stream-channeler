from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.channels.models import Channel, ChannelQueue, ChannelTitle
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.channels.service.ordering import order_preset_options
from app.models import Visibility
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.users.service.accounts import get_or_create_automatic_channel_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable, Sequence

    from app.plugins.models import Plugin


class BaseChannelMixin(AbstractPlugin, ABC):
    session: Session
    plugin: Plugin

    @classmethod
    @abstractmethod
    def source_name(cls) -> str: ...

    @cached_property
    def automatic_channel_user(self) -> User:
        return get_or_create_automatic_channel_user(self.session, self.source_name())

    def get_or_create_channel(
        self,
        channel_name: str,
        channel_description: str,
    ) -> Channel:
        """Return the channel belonging to the source, creating it if it does not exist."""
        user = self.automatic_channel_user
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == user.id)
            .where(Channel.name == channel_name),
        ).one_or_none()
        if not channel:
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
                user_id=user.id,
            )
            self.session.add(channel)
            self.session.flush()
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
        title_keys_by_url = {url: self.title_key_from_url(url) for url in urls}
        titles = self.session.exec(
            select(Title)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(Title.key).in_(set(title_keys_by_url.values())),
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
    def _add_titles_to_all_titles_channel(self, title_keys: Iterable[str]) -> None:
        urls = [self.title_url(title_key) for title_key in title_keys]
        self.add_new_urls_to_channel("All Titles", urls)

    # TODO: Validate
    def add_new_urls_to_channel(
        self,
        channel_key: str,
        urls: Sequence[str],
    ) -> None:
        if not urls:
            return

        channel = self.get_or_create_channel(
            self._channel_name(channel_key),
            self._channel_description(channel_key),
        )
        urls_not_in_queue = self._urls_not_in_queue(channel, urls)
        if new_urls := self._urls_not_on_channel(channel, urls_not_in_queue):
            add_urls_to_channel_import_queue(
                self.session,
                channel,
                new_urls,
            )

    # TODO: Validate
    def _urls_not_on_channel(self, channel: Channel, urls: Sequence[str]) -> list[str]:
        if not urls:
            return []
        titles_by_url = self._titles_by_url(
            {url for url in urls if self._has_title_key(url)},
        )
        channel_tmdb_title_ids = set(
            self.session.exec(
                select(ChannelTitle.tmdb_title_id).where(
                    ChannelTitle.channel_id == channel.id,
                ),
            ).all(),
        )
        return [
            url
            for url in urls
            if not (tmdb_title_ids := self._tmdb_title_ids(titles_by_url.get(url, [])))
            or not tmdb_title_ids <= channel_tmdb_title_ids
        ]

    # TODO: Validate
    def _has_title_key(self, url: str) -> bool:
        try:
            self.title_key_from_url(url)
        except InvalidURLError:
            return False
        return True

    # TODO: Validate
    @staticmethod
    def _tmdb_title_ids(titles: Sequence[Title]) -> set[uuid.UUID]:
        return {
            tmdb_title_id
            for title in titles
            for tmdb_title_id in (title.tmdb_title_ids or [title.id])
        }

    def _urls_not_in_queue(self, channel: Channel, urls: Sequence[str]) -> list[str]:
        """Return the URLs that are not currently in the channel's import queue."""
        queued_urls = set(
            self.session.exec(
                select(ChannelQueue.url).where(
                    ChannelQueue.channel_id == channel.id,
                    col(ChannelQueue.url).in_(urls),
                ),
            ).all(),
        )
        return [url for url in urls if url not in queued_urls]

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
