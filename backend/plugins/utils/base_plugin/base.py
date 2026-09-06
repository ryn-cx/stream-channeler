# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast, override

from sqlmodel import Session, select

from app.channels.models import Channel
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.channels.service.ordering import order_preset_options
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.models import Visibility
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.users.models import User
from app.users.service.accounts import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    TMDBLookupInfo,
    URLImportResult,
)
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.update import BaseUpdateMixin
from plugins.utils.base_plugin.url import BaseURLMixin, MediaInfo

if TYPE_CHECKING:
    from plugins.utils.base_plugin.importer import BaseImporter


# TODO: Validate
class BasePlugin(BaseUpdateMixin, BaseURLMixin, ABC):
    __plugin_channels: tuple[User, dict[str, Channel]] | None = None

    if TYPE_CHECKING:
        # TODO: Validate
        def search_for_url(
            self,
            names: list[str],
            media_type: TMDBMediaType,
            year: int | None = None,
        ) -> str | None: ...

    # TODO: Validate
    @property
    def source(self) -> Source:
        return self._sources[self.source_name()]

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
                default_order=order_preset_options(self.session, "Roll The Dice"),
                update_at=tz_datetime.now() + timedelta(days=1),
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
            plugin_user = get_or_create_plugin_user(
                session=self.session,
                plugin_name=self.plugin_name(),
            )
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
        title_key: str,  # noqa: ARG002 - `title_key` is used by overrides.
    ) -> list[TMDBLookupInfo]:
        return []

    # TODO: Validate
    def link_title_to_tmdb(self, title: Title) -> None:
        from app.titles.service.canonical import (  # noqa: PLC0415
            link_title_to_tmdb_lookups,
        )

        # self.session.commit()
        link_title_to_tmdb_lookups(
            self.session,
            title,
            self.tmdb_lookup_info(title.key),
        )

    # TODO: Validate
    @classmethod
    def initialize_plugin(cls, session: Session) -> None:
        cls.initializer.initialize_plugin(session)

    # TODO: Validate
    def _get_media_importer_from_url(self, url: str) -> BaseImporter:  # noqa: ARG002
        return cast("BaseImporter", self)

    # TODO: Validate
    def _get_media_importer_from_title(self, title: Title) -> BaseImporter:  # noqa: ARG002
        return cast("BaseImporter", self)

    # TODO: Validate
    def get_media_importer_from_source(self, source: Source) -> BaseImporter:  # noqa: ARG002
        """Get the media importer to use based on the source."""
        return cast("BaseImporter", self)

    # TODO: Validate
    def import_url(self, url: str) -> list[URLImportResult]:
        return self._get_media_importer_from_url(url).import_url(url)

    # TODO: Validate
    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> list[URLImportResult]:
        url = self.search_for_url(names, media_type, year)
        if url:
            return self.import_url(url)
        return []

    # TODO: Validate
    def update_source(self, source: Source, update_at: datetime) -> None:
        self.get_media_importer_from_source(source).update_source(source, update_at)

    # TODO: Validate
    def update_title(self, title: Title, *, force: bool = False) -> None:
        self._get_media_importer_from_title(title).update_title(title, force=force)

    # TODO: Validate
    def update_season(self, season: Season) -> None:
        self._get_media_importer_from_title(season.title).update_season(season)

    # TODO: Validate
    def update_episode(self, episode: Episode) -> None:
        self._get_media_importer_from_title(episode.season.title).update_episode(
            episode,
        )

    # TODO: Validate
    def on_update_title_failure(self, title: Title, error: Exception) -> None:
        self._get_media_importer_from_title(title).on_failure(title, error)

    # TODO: Validate
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self._get_media_importer_from_title(season.title).on_failure(season, error)

    # TODO: Validate
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self._get_media_importer_from_title(episode.season.title).on_failure(
            episode, error,
        )

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
    def extract_media_info(self, url: str) -> MediaInfo:
        msg = f"{self.plugin_name()} does not implement extract_media_info"
        raise NotImplementedError(msg)

    # TODO: Validate
    def _import_results(
        self,
        title: Title,
        media_info: MediaInfo | None = None,
    ) -> list[URLImportResult]:
        result_titles = [title, *title.canonical_titles]

        if media_info and media_info.episode_key is not None:
            episodes = [self._imported_episode(title, media_info.episode_key)]
            return [
                URLImportResult.episode_import_results(result_title, episodes)
                for result_title in result_titles
            ]

        if media_info and media_info.season_key is not None:
            seasons = [self._imported_season(title, media_info.season_key)]
            return [
                URLImportResult.season_import_results(result_title, seasons)
                for result_title in result_titles
            ]

        return [
            URLImportResult.title_import_results(result_title)
            for result_title in result_titles
        ]

    # TODO: Validate
    def _imported_season(self, title: Title, season_key: str) -> Season:
        for season in title.seasons:
            if season.key == season_key:
                return season

        msg = f"Season {season_key} not found in title {title.key}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _imported_episode(self, title: Title, episode_key: str) -> Episode:
        for season in title.seasons:
            for episode in season.episodes:
                if episode.key == episode_key:
                    return episode

        msg = f"Episode {episode_key} not found in title {title.key}"
        raise InvalidURLError(msg)
