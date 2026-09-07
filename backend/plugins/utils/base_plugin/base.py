# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, cast, override

from sqlalchemy import or_
from sqlmodel import Session, col, select

from app.channels.models import Channel, ChannelTitle
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.channels.service.ordering import order_preset_options
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.models import Visibility
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title, TitleCanonicalTitle
from app.users.service.accounts import get_or_create_plugin_user
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.update import BaseUpdateMixin
from plugins.utils.base_plugin.url import BaseURLMixin, URLTitleInfo

if TYPE_CHECKING:
    from plugins.utils.base_plugin.importer import BaseImporter


# TODO: Validate
class BasePlugin(BaseUpdateMixin, BaseURLMixin, ABC):
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
    def get_or_create_channel(
        self,
        channel_name: str,
        channel_description: str,
    ) -> Channel:
        """Return the plugin owned channel `name`, creating it the first time."""
        plugin_user = get_or_create_plugin_user(
            session=self.session,
            plugin_name=self.plugin_name(),
        )
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == plugin_user.id)
            .where(Channel.name == channel_name),
        ).one_or_none()
        if channel is None:
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
        return channel

    # TODO: Validate
    def _channel_name(self, subject: str) -> str:
        return f"{subject} on {self.source_name()}"

    # TODO: Validate
    def _channel_description(self, subject: str) -> str:
        return f"All {subject.removeprefix('All ')} titles on {self.source_name()}."

    # TODO: Validate
    def _add_urls_to_channel_by_prefix(
        self,
        urls: Sequence[str],
        channel_prefix: str,
    ) -> None:
        channel = self.get_or_create_channel(
            self._channel_name(channel_prefix),
            self._channel_description(channel_prefix),
        )
        self.add_new_urls_to_channel(channel, urls)

    # TODO: Validate
    def add_new_urls_to_channel(self, channel: Channel, urls: Sequence[str]) -> None:
        urls_not_on_channel = self._urls_not_on_channel(channel, urls)
        add_urls_to_channel_import_queue(self.session, channel, urls_not_on_channel)

    # TODO: Validate
    def _urls_not_on_channel(self, channel: Channel, urls: Sequence[str]) -> list[str]:
        channel_canonical_title_ids = select(ChannelTitle.canonical_title_id).where(
            ChannelTitle.channel_id == channel.id,
        )
        on_channel_urls = set(
            self.session.exec(
                select(Title.url).where(
                    col(Title.url).in_(urls),
                    or_(
                        col(Title.id).in_(channel_canonical_title_ids),
                        col(Title.id).in_(
                            select(TitleCanonicalTitle.title_id).where(
                                col(TitleCanonicalTitle.canonical_title_id).in_(
                                    channel_canonical_title_ids,
                                ),
                            ),
                        ),
                    ),
                ),
            ).all(),
        )
        return [url for url in urls if url not in on_channel_urls]

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
            episode,
            error,
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
    def get_media_info(self, url: str) -> URLTitleInfo:
        """Return information about the title extracted from the URL.

        In some situations this may require network requests."""
        msg = f"{self.plugin_name()} does not implement get_media_info"
        raise NotImplementedError(msg)

    # TODO: Validate
    def _import_results(
        self,
        title: Title,
        media_info: URLTitleInfo | None = None,
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
