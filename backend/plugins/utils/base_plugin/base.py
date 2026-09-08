# TODO: Validate
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta
from functools import singledispatchmethod
from typing import TYPE_CHECKING, Any, ClassVar, TypeIs, override

from sqlalchemy import or_
from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, select

from app.channels.models import Channel, ChannelTitle
from app.channels.service.import_queue import add_urls_to_channel_import_queue
from app.channels.service.ordering import order_preset_options
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.episodes.preload import preload_episodes
from app.media.media_type import TMDBMediaType
from app.models import BaseMediaMixin, Visibility
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title, TitleCanonicalTitle
from app.users.service.accounts import get_or_create_plugin_user
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    TMDBLookupInfo,
    URLImportResult,
)
from plugins.utils.base_plugin.file_access import BaseFileAccessMixin
from plugins.utils.base_plugin.url import BaseURLMixin, URLTitleInfo

if TYPE_CHECKING:
    from plugins.utils.base_plugin.importer import BaseImporter
    from plugins.utils.base_plugin.initialize import BasePluginInitializer


# TODO: Validate
class BasePlugin(BaseFileAccessMixin, BaseURLMixin, AbstractPlugin, ABC):
    initializer: ClassVar[type[BasePluginInitializer]]

    # TODO: Validate
    @override
    def __init__(self, session: Session, plugin: Plugin | None = None) -> None:
        """Initialize the plugin.

        Args:
            session: The SQLAlchemy session to use for database operations.
            plugin: An optional `Plugin` instance to use instead of fetching it from the
            database.
        """
        self.session = session
        self.plugin = plugin or Plugin.get_one(session, self.plugin_name())
        """The `Plugin` record from the database."""
        self._sources = {source.key: source for source in self.plugin.sources}
        """All of the `Source` records from the database in a dict keyed by
        `Source.key`."""
        self._file_cache = {}

    # TODO: Validate
    @classmethod
    @abstractmethod
    def plugin_name(cls) -> str: ...

    # TODO: Validate
    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    # TODO: Validate
    @classmethod
    def source_name(cls) -> str:
        return cls.plugin_name()

    # TODO: Validate
    @classmethod
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def link_to_tmdb(cls) -> bool:
        return True

    # TODO: Validate
    @classmethod
    def _source_keys(cls) -> tuple[str, ...]:
        return (cls.plugin_name(),)

    # TODO: Validate
    @classmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        return provider_name in cls.name_on_tmdb()

    # TODO: Validate
    def _title_is_outdated(
        self,
        title: Title | None,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if title is None or force:
            return True
        return self._record_is_outdated(
            title,
            self._title_files_data_timestamp(title.key),
        )

    # TODO: Validate
    def _season_is_outdated(
        self,
        season: Season | None,
        title_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if season is None or force:
            return True
        return self._record_is_outdated(
            season,
            self._season_files_data_timestamp(season.key, title_key),
        )

    # TODO: Validate
    def _episode_is_outdated(
        self,
        episode: Episode | None,
        season_key: str,
        title_key: str,
        *,
        force: bool = False,
    ) -> TypeIs[None]:
        if episode is None or force:
            return True
        return self._record_is_outdated(
            episode,
            self._episode_files_data_timestamp(episode.key, season_key, title_key),
        )

    # TODO: Validate
    @staticmethod
    def _record_is_outdated(record: BaseMediaMixin, data_timestamp: datetime) -> bool:
        return record.data_timestamp != data_timestamp or record.deleted_at is not None

    # TODO: Validate
    def _preload_sources(
        self,
        source_key: str | list[str] | None = None,
        *,
        preload_titles: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Source]:
        """Preload the sources with optional related titles, seasons, and episodes.

        If no source_key is provided, all sources for the plugin will be preloaded.
        """
        options: list[Any] = []
        if preload_episodes:
            options.append(
                selectinload(Source.titles)  # type: ignore[arg-type]
                .selectinload(Title.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes),  # type: ignore[arg-type]
            )
        elif preload_seasons:
            options.append(
                selectinload(Source.titles).selectinload(Title.seasons),  # type: ignore[arg-type]  # type: ignore[arg-type]
            )
        elif preload_titles:
            options.append(selectinload(Source.titles))  # type: ignore[arg-type]
        statement = select(Source).where(Source.plugin_id == self.plugin.id)
        if isinstance(source_key, list):
            statement = statement.where(Source.key.in_(source_key))  # type: ignore[attr-defined]
        elif source_key:
            statement = statement.where(Source.key == source_key)
        return self.session.exec(statement.options(*options)).unique()

    # TODO: Validate
    def _preload_title(
        self,
        title: str | uuid.UUID,
        source_key: str | None = None,
        *,
        preload_source: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Title]:
        options: list[Any] = []
        if preload_source:
            options.append(joinedload(Title.source))  # type: ignore[arg-type]
        if preload_episodes:
            # What each episode already stands for is read with it, because
            # pointing an episode at another one reads the link it is replacing,
            # and that read is a query of its own however many rows the session
            # is already holding: `Episode.id` is unique rather than the primary
            # key, so nothing can be answered out of the session by it. Read here
            # it is one query for every episode of the listing instead of one
            # each.
            options.append(
                selectinload(Title.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes)  # type: ignore[arg-type]
                .selectinload(Episode.canonical_episode_links)  # type: ignore[arg-type]
                .selectinload(EpisodeCanonicalEpisode.canonical_episode),  # type: ignore[arg-type]
            )
        elif preload_seasons:
            options.append(selectinload(Title.seasons))  # type: ignore[arg-type]
        if isinstance(title, uuid.UUID):
            statement = select(Title).where(Title.id == title)
        else:
            statement = (
                select(Title)
                .join(Source)
                .where(Source.plugin_id == self.plugin.id, Title.key == title)
            )
            if source_key is not None:
                statement = statement.where(Source.key == source_key)
        return self.session.exec(statement.options(*options)).unique()

    # TODO: Validate
    def _preload_season(
        self,
        season_id: uuid.UUID,
        *,
        preload_source: bool = False,
        preload_title: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Season]:
        options: list[Any] = []
        if preload_source:
            options.append(joinedload(Season.title).joinedload(Title.source))  # type: ignore[arg-type]
        elif preload_title:
            options.append(joinedload(Season.title))  # type: ignore[arg-type]
        if preload_episodes:
            options.append(selectinload(Season.episodes))  # type: ignore[arg-type]
        return self.session.exec(
            select(Season).where(Season.id == season_id).options(*options),
        )

    # TODO: Validate
    def _preload_episode(
        self,
        episode_id: uuid.UUID,
        *,
        preload_source: bool = False,
        preload_title: bool = False,
        preload_season: bool = False,
    ) -> ScalarResult[Episode]:
        options: list[Any] = []
        if preload_source:
            options.append(
                joinedload(Episode.season)  # type: ignore[arg-type]
                .joinedload(Season.title)  # type: ignore[arg-type]
                .joinedload(Title.source),  # type: ignore[arg-type]
            )
        elif preload_title:
            options.append(
                joinedload(Episode.season).joinedload(Season.title),  # type: ignore[arg-type]
            )
        elif preload_season:
            options.append(joinedload(Episode.season))  # type: ignore[arg-type]
        return self.session.exec(
            select(Episode).where(Episode.id == episode_id).options(*options),
        )

    # TODO: Validate
    @staticmethod
    def _existing_data_timestamp_or_now(record: BaseMediaMixin | None) -> datetime:
        """Return the record's data timestamp, or the current time if it has none."""
        if record and record.data_timestamp:
            return record.data_timestamp
        return tz_datetime.now()

    # TODO: Validate
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        """Store the listing `title_key` names."""
        # Not an abstractmethod, because a plugin that reads a title as one of
        # several kinds writes each kind on its own and has nothing to write for
        # a title it has not been told the kind of. Such a plugin is still a
        # plugin, so what it cannot answer is raised when asked rather than kept
        # from being built at all.
        msg = f"{self.plugin_name()} does not upsert titles."
        raise NotImplementedError(msg)

    # TODO: Validate
    def upsert_source(self, source_key: str) -> Source:
        """Create or update the plugin's `Source` record(s)."""
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            favicon_url=self.favicon_url(),
            link_to_tmdb=self.link_to_tmdb(),
            data_timestamp=self._existing_data_timestamp_or_now(existing_source),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source

    # TODO: Validate
    def soft_delete_missing_seasons(self, title_key: str) -> None:
        """Soft-delete seasons whose keys are not in the title's season file."""
        season_keys = self._season_keys_from_title_files(title_key)
        for title in self._preload_title(title_key, preload_seasons=True).all():
            title.soft_delete_missing_children(season_keys)

    # TODO: Validate
    def _soft_delete_missing_episodes(self, season_key: str, title_key: str) -> None:
        """Soft-delete episodes whose keys are not in the season's episode file."""
        episode_keys = self._episode_keys_from_season_files(season_key, title_key)
        for title in self._preload_title(title_key, preload_seasons=True).all():
            for season in title.seasons:
                if season.key == season_key:
                    season.soft_delete_missing_children(episode_keys)

    # TODO: Validate
    def _soft_delete_missing(self, title_key: str) -> None:
        self.soft_delete_missing_seasons(title_key)
        for season_key in self._season_keys_from_title_files(title_key):
            self._soft_delete_missing_episodes(season_key, title_key)

    # TODO: Validate
    def _mark_mismatched_titles_as_outdated(
        self,
        source_key: str | None,
        new_title_keys: Iterable[str],
        data_timestamps: list[datetime],
    ) -> None:
        listed = set(new_title_keys)
        for source in self._preload_sources(source_key, preload_titles=True):
            for title in source.titles:
                is_listed = title.key in listed
                is_deleted = title.deleted_at is not None
                if is_listed == is_deleted:
                    title.set_update_at(min(data_timestamps))

    # TODO: Validate
    def _set_season_update_at_based_on_last_episode(self, season: Season) -> None:
        if not season.data_timestamp:  # Should be impossible
            msg = f"Record {season.key} has no data_timestamp"
            raise ValueError(msg)

        preload_episodes(self.session, [season.title])
        data_timestamps = self._season_files_data_timestamps(
            season.key,
            season.title.key,
        )
        for episode in season.active_children:
            if episode.air_date:
                season.set_update_at(episode.air_date)
                season.set_update_at(
                    episode.air_date + timedelta(days=7),
                )
                # Buffer days due to possible timestamp offsets
                season.set_update_at(
                    episode.air_date + timedelta(days=8),
                )
                season.set_update_at(
                    episode.air_date + timedelta(days=9),
                )
        season.set_update_at(
            staggered_monthly_update_at(season.key, min(data_timestamps)),
        )

    if TYPE_CHECKING:
        # TODO: Validate
        def search_for_title_url(
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
        self._add_new_urls_to_channel(channel, urls)

    # TODO: Validate
    def _add_new_urls_to_channel(self, channel: Channel, urls: Sequence[str]) -> None:
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
    @singledispatchmethod
    def _media_importer(self, url_or_title: str | Title) -> BaseImporter:  # noqa: ARG002
        raise TypeError

    # TODO: Validate
    @_media_importer.register(str)
    def _(self, url: str) -> BaseImporter:
        return self._media_importer_from_url(url)

    # TODO: Validate
    @_media_importer.register(Title)
    def _(self, title: Title) -> BaseImporter:
        return self._media_importer_from_title(title)

    # TODO: Validate
    def _validate_url(self, url: str) -> None:
        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _media_importer_from_url(self, url: str) -> BaseImporter:  # noqa: ARG002
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    # TODO: Validate
    def _media_importer_from_title(self, title: Title) -> BaseImporter:  # noqa: ARG002
        return self  # type: ignore[return-value]  # ty: ignore[invalid-return-type]

    # TODO: Validate
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        if not title.name:
            return []
        media_type = (
            TMDBMediaType.movie if title.media_type == "Movie" else TMDBMediaType.tv
        )
        return [TMDBLookupInfo(title.name, media_type, title.year)]

    # TODO: Validate
    def validate_and_import_url(self, url: str) -> list[URLImportResult]:
        self._validate_url(url)
        return self._media_importer(url).import_url(url)

    # TODO: Validate
    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> list[URLImportResult]:
        url = self.search_for_title_url(names, media_type, year)
        if url:
            return self.validate_and_import_url(url)
        return []

    # TODO: Validate
    def update_title(self, title: Title, *, force: bool = False) -> None:
        self._media_importer(title).update_title(title, force=force)

    # TODO: Validate
    def update_season(self, season: Season) -> None:
        self._media_importer(season.title).update_season(season)

    # TODO: Validate
    def update_episode(self, episode: Episode) -> None:
        self._media_importer(episode.season.title).update_episode(
            episode,
        )

    # TODO: Validate
    def on_update_title_failure(self, title: Title, error: Exception) -> None:
        self._media_importer(title).on_failure(title, error)

    # TODO: Validate
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        self._media_importer(season.title).on_failure(season, error)

    # TODO: Validate
    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:
        self._media_importer(episode.season.title).on_failure(
            episode,
            error,
        )


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
