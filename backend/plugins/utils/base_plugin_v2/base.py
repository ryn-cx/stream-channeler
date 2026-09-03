# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, override

from sqlmodel import Session, select

from app.channels.models import Channel
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.episodes.models import Episode
from app.models import Visibility
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User
from app.users.service import get_or_create_plugin_user
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    TMDBLookupInfo,
    URLImportResult,
)
from plugins.utils.base_plugin_v2.files import BaseFile
from plugins.utils.base_plugin_v2.update import BaseUpdateMixin
from plugins.utils.base_plugin_v2.url import BaseURLMixin


# TODO: Validate
class BasePlugin(BaseUpdateMixin, BaseURLMixin, ABC):
    __plugin_channels: tuple[User, dict[str, Channel]] | None = None

    # TODO: Validate
    def add_urls_to_plugin_channel(
        self,
        channel_name: str,
        channel_description: str,
        urls: Sequence[str] = (),
    ) -> Channel:
        """Return the plugin owned channel `name`, creating it the first time."""
        plugin_user, channels = self._plugin_channels()
        if not (channel := channels.get(channel_name)):
            channel = Channel(
                name=channel_name,
                description=channel_description,
                visibility=Visibility.public,
                anonymous=False,
                score=-1,
                user_id=plugin_user.id,
            )
            self.session.add(channel)
            self.session.flush()
            channels[channel_name] = channel
        add_urls_to_channel_import_queue(self.session, channel, urls)
        return channel

    # TODO: Validate
    def _plugin_channels(self) -> tuple[User, dict[str, Channel]]:
        """Return every channel the plugin user owns, read once per plugin.

        A plugin whose catalogue is split across a hundred genres asks for a
        hundred channels, and reading each one on its own is a query each.
        """
        if self.__plugin_channels is None:
            plugin_user = get_or_create_plugin_user(session=self.session)
            self.__plugin_channels = (
                plugin_user,
                {
                    channel.name: channel
                    for channel in self.session.exec(
                        select(Channel).where(Channel.user_id == plugin_user.id),
                    ).all()
                },
            )
        return self.__plugin_channels

    # TODO: Validate
    def tmdb_lookup_info(self, show_key: str) -> TMDBLookupInfo
        msg = f"{self.plugin_name()} does not support TMDB lookups."
        raise NotImplementedError(msg)

    # TODO: Validate
    def find_tmdb_show_record(self, show_key: str) -> Show | None:
        tmdb_lookup_info = self.tmdb_lookup_info(show_key)
        from plugins.TMDB import TMDB  # noqa: PLC0415

        return TMDB(self.session).import_search(tmdb_lookup_info)

    # TODO: Validate
    @classmethod
    def initialize_plugin(cls, session: Session) -> None:
        cls.initializer.initialize_plugin(session)

    # TODO: Validate
    @classmethod
    def url_regex(cls) -> str:
        return cls.importer.url_regex()

    # TODO: Validate
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        return self.importer(self).import_url(url, canonical_show)

    # TODO: Validate
    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        self.importer(self).on_failure(show, error)

    # TODO: Validate
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self.importer(self).on_failure(season, error)

    # TODO: Validate
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self.importer(self).on_failure(episode, error)

    # TODO: Validate
    def raise_if_invalid_file(self, file: BaseFile[Any], url: str) -> None:
        file.download_if_outdated()
        if not file.database_record.content:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)


# TODO: Validate
class BaseReadURL(BasePlugin, ABC):
    # TODO: Validate
    @classmethod
    @abstractmethod
    def _url_regexes(cls) -> tuple[str, ...]: ...

    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        domain_regex = cls._domain_regex()
        alternatives = "|".join(
            domain_regex + url_regex for url_regex in cls._url_regexes()
        )
        return f"(?:{alternatives})"

    # TODO: Validate
    @abstractmethod
    def _parse_url(self, url: str) -> str: ...

    # TODO: Validate
    def _import_results(self, show: Show) -> list[URLImportResult]:
        results = [URLImportResult.show_import_results(show)]
        results += [
            URLImportResult.show_import_results(canonical_show)
            for canonical_show in show.canonical_shows
        ]
        return results
