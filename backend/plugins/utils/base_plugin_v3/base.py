# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, override

from sqlmodel import Session, select

from app.channels.models import Channel
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.models import Visibility
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.users.service.accounts import get_or_create_plugin_user
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v3.files import BaseFile
from plugins.utils.base_plugin_v3.update import BaseUpdateMixin
from plugins.utils.base_plugin_v3.url import BaseURLMixin

if TYPE_CHECKING:
    from plugins.utils.base_plugin_v3.importer import BaseImporter


# TODO: Validate
class BasePlugin(BaseUpdateMixin, BaseURLMixin, ABC):
    __plugin_channels: tuple[User, dict[str, Channel]] | None = None

    if TYPE_CHECKING:
        # TODO: Validate
        def best_matching_title_url(
            self,
            names: list[str],
            media_type: TMDBMediaType,
            year: int | None = None,
        ) -> str | None: ...

    # TODO: Validate
    @property
    def source(self) -> Source:
        return self._sources[self.plugin_name()]

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
    def tmdb_lookup_info(
        self,
        show_key: str,
    ) -> tuple[str, TMDBMediaType | None, int | None]:
        msg = f"{self.plugin_name()} does not support TMDB lookups."
        raise NotImplementedError(msg)

    # TODO: Validate
    @classmethod
    def initialize_plugin(cls, session: Session) -> None:
        cls.initializer.initialize_plugin(session)

    # TODO: Validate
    def get_media_importer(self, media: Show | str) -> BaseImporter:
        msg = f"{self.plugin_name()} does not dispatch media to an importer."
        raise NotImplementedError(msg)

    def import_url(self, url: str) -> list[URLImportResult]:
        return self.get_media_importer(url).import_url(url)

    # TODO: Validate
    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> list[URLImportResult]:
        url = self.best_matching_title_url(names, media_type, year)
        if url:
            return self.import_url(url)
        return []

    def update_show(self, show: Show, *, force: bool = False) -> None:
        self.get_media_importer(show).update_show(show, force=force)

    def update_season(self, season: Season) -> None:
        self.get_media_importer(season.show).update_season(season)

    def update_episode(self, episode: Episode) -> None:
        self.get_media_importer(episode.season.show).update_episode(episode)

    def on_update_show_failure(self, show: Show, error: Exception) -> None:
        self.get_media_importer(show).on_failure(show, error)

    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self.get_media_importer(season.show).on_failure(season, error)

    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self.get_media_importer(episode.season.show).on_failure(episode, error)

    # TODO: Validate
    def raise_if_invalid_file(self, file: BaseFile[Any], url: str) -> None:
        if file.parsed_or_none() is None:
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
    @override
    def _url_to_show_key(self, url: str) -> str:
        msg = f"{self.plugin_name()} does not implement _url_to_show_key"
        raise NotImplementedError(msg)

    # TODO: Validate
    def _import_results(
        self,
        show: Show,
        *_args: Any,  # noqa: ANN401
        **_kwargs: Any,  # noqa: ANN401
    ) -> list[URLImportResult]:
        results = [URLImportResult.show_import_results(show)]
        results += [
            URLImportResult.show_import_results(canonical_show)
            for canonical_show in show.canonical_shows
        ]
        return results
