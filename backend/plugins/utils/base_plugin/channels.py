# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.channels.models import Channel, ChannelQueue
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.channels.service.ordering import order_preset_options
from app.models import Visibility
from app.sources.models import Source
from app.titles.models import Title, TitleCanonicalTitle
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.users.service.accounts import get_or_create_automatic_channel_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

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

    def _add_urls_to_channel(self, urls: Sequence[str], title_prefix: str) -> None:
        """Add the given URLs to the channel specified using the title prefix."""
        channel = self.get_or_create_channel(
            self._channel_name(title_prefix),
            self._channel_description(title_prefix),
        )

        urls_not_in_queue = self._urls_not_in_queue(channel, urls)
        add_urls_to_channel_import_queue(self.session, channel, urls_not_in_queue)

    # TODO: Validate
    def _urls_not_in_queue(self, channel: Channel, urls: Sequence[str]) -> list[str]:
        queued_urls = set(
            self.session.exec(
                select(ChannelQueue.url).where(
                    ChannelQueue.channel_id == channel.id,
                    col(ChannelQueue.url).in_(urls),
                ),
            ).all(),
        )
        return [url for url in urls if url not in queued_urls]

    # TODO: Validate
    def _remove_unlisted_queued_urls(self, channel: Channel) -> None:
        """Drop the queued URLs of an automatic channel that the website dropped."""
        queue_rows = self.session.exec(
            select(ChannelQueue)
            .join(Channel, col(Channel.id) == col(ChannelQueue.channel_id))
            .join(User, col(User.id) == col(Channel.user_id))
            .where(
                ChannelQueue.channel_id == channel.id,
                is_plugin_user(User.email),
            ),
        ).all()
        if not queue_rows:
            return

        unlisted_urls = self._unlisted_urls({queue_row.url for queue_row in queue_rows})
        for queue_row in queue_rows:
            if queue_row.url in unlisted_urls:
                self.session.delete(queue_row)

    # TODO: Validate
    def _unlisted_urls(self, urls: set[str]) -> set[str]:
        """Return the URLs the plugin holds nothing but deleted titles for.

        A URL the plugin holds no title for at all is not answered with, because it
        is a URL waiting to be imported rather than one the website dropped.
        """
        titles = self.session.exec(
            select(Title)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(Title.url).in_(urls),
            )
            .options(selectinload(Title.canonical_title_links)),  # type: ignore[arg-type]
        ).all()

        titles_by_url: dict[str, list[Title]] = {}
        for title in titles:
            if title.url:
                titles_by_url.setdefault(title.url, []).append(title)

        canonical_ids_by_url = {
            url: {
                canonical_title_id
                for title in url_titles
                for canonical_title_id in title.canonical_title_ids
            }
            for url, url_titles in titles_by_url.items()
            if all(title.deleted_at is not None for title in url_titles)
        }
        listed_canonical_title_ids = self._listed_canonical_title_ids(
            {
                canonical_title_id
                for canonical_title_ids in canonical_ids_by_url.values()
                for canonical_title_id in canonical_title_ids
            },
        )
        return {
            url
            for url, canonical_title_ids in canonical_ids_by_url.items()
            if not canonical_title_ids & listed_canonical_title_ids
        }

    # TODO: Validate
    def _listed_canonical_title_ids(
        self,
        canonical_title_ids: set[uuid.UUID],
    ) -> set[uuid.UUID]:
        """Return the canonical titles the plugin still holds a live title for."""
        if not canonical_title_ids:
            return set()

        listed_ids = self.session.exec(
            select(Title.id)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(Title.id).in_(canonical_title_ids),
                col(Title.deleted_at).is_(None),
            ),
        ).all()
        linked_ids = self.session.exec(
            select(TitleCanonicalTitle.canonical_title_id)
            .join(Title, col(Title.id) == col(TitleCanonicalTitle.title_id))
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                col(TitleCanonicalTitle.canonical_title_id).in_(canonical_title_ids),
                col(Title.deleted_at).is_(None),
            ),
        ).all()
        return set(listed_ids) | set(linked_ids)
