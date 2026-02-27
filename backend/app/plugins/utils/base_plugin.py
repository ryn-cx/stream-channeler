# TODO: Validate
import re
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime
from functools import cache
from typing import Any, TypeIs, override

from sqlalchemy.orm import joinedload
from sqlmodel import Session, SQLModel, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.media.models import Episode, EpisodeWatch, File, Plugin, Season, Show, Source
from app.media.schemas import PluginInput
from app.plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from app.plugins.utils.base_files import BaseFile
from app.users.models import User
from app.utils import tz_datetime


class BasePlugin(AbstractPlugin, ABC, register=False):
    # region Initialization

    @override
    def __init__(
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        self.db = db
        self.__show_id_value: str | None = None
        self.__plugin_value: Plugin | None = None
        self._preload_cache: list[SQLModel] = []
        self.__preload_plugin()
        self.__upsert_plugin()

    def __preload_plugin(self) -> None:
        # assignment - The setter is designed to handle a Plugin or None value.
        self.plugin = Plugin.get(  # type: ignore[assignment]
            self.db,
            self.plugin_id(),
            # reportArgumentType - joinedload always has type errors.
            options=[joinedload(Plugin.sources)],  # type: ignore[arg-type]
            populate_existing=True,
        )

    def __upsert_plugin(self) -> None:
        # Only update the data_timestamp if the data changes.
        if self._has_plugin() and self.plugin.name == self._plugin_name():
            data_timestamp = self.plugin.data_timestamp
        else:
            data_timestamp = tz_datetime.now()

        self.plugin = PluginInput(
            key=self.plugin_id(),
            name=self._plugin_name(),
            data_timestamp=data_timestamp,
        ).upsert(self.db, self._has_plugin())

    # endregion

    # region Preload

    def _add_all_to_preload_cache[T: SQLModel](
        self,
        statement: SelectOfScalar[T],
    ) -> Sequence[T]:
        """Execute query and preload all of the results."""
        results = self.db.exec(statement).unique().all()
        # Add File objects to plugin_v2 cache to prevent garbage collection
        self._preload_cache.extend(results)
        return results

    def _add_first_to_preload_cache[T: SQLModel](
        self,
        statement: SelectOfScalar[T],
    ) -> T | None:
        """Execute query and preload the first result."""
        if result := self.db.exec(statement).first():
            self._preload_cache.append(result)
            return result

        return None

    def _add_one_to_preload_cache[T: SQLModel](
        self,
        statement: SelectOfScalar[T],
    ) -> T:
        """Execute query and if there is only one result preload it."""
        result = self.db.exec(statement).unique().one()
        self._preload_cache.append(result)
        return result

    def _add_one_or_none_to_preload_cache[T: SQLModel](
        self,
        statement: SelectOfScalar[T],
    ) -> T | None:
        """Execute query and if there is at most one result preload it."""
        results = self.db.exec(statement).unique().one_or_none()
        if results:
            self._preload_cache.append(results)
        return results

    def _preload_shows_statement(
        self,
        *,
        preload_sources: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> SelectOfScalar[Show]:
        options: list[Any] = []
        if preload_sources:
            options.append(joinedload(Show.source))
        if preload_episodes:
            options.append(joinedload(Show.seasons).joinedload(Season.episodes))
        elif preload_seasons:
            options.append(joinedload(Show.seasons))
        return (
            select(Show)
            .join(Source)
            .where(
                Source.plugin_id == self.plugin.id,
                Show.key == self._show_id,
            )
            .options(*options)
        )

    def _preload_shows(
        self,
        *,
        preload_sources: bool = True,
        preload_seasons: bool = True,
        preload_episodes: bool = True,
    ) -> Sequence[Show] | None:
        statement = self._preload_shows_statement(
            preload_sources=preload_sources,
            preload_seasons=preload_seasons,
            preload_episodes=preload_episodes,
        )
        return self._add_all_to_preload_cache(statement)

    def _preload_show(
        self,
        *,
        preload_sources: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> Show | None:
        statement = self._preload_shows_statement(
            preload_sources=preload_sources,
            preload_seasons=preload_seasons,
            preload_episodes=preload_episodes,
        )
        return self._add_one_or_none_to_preload_cache(statement)

    def _preload_all_plugin_files(self) -> Sequence[File]:
        """Preload all of the files that belong to a plugin."""
        statement = select(File).where(File.plugin == self.plugin)
        return self._add_all_to_preload_cache(statement)

    def list_is_all_uuids(
        self,
        items: list[uuid.UUID] | list[str] | SelectOfScalar[File],
    ) -> TypeIs[list[uuid.UUID]]:
        """Check if the list is all UUIDs or all strings."""
        if isinstance(items, SelectOfScalar):
            return False
        return all(isinstance(item, uuid.UUID) for item in items)

    def list_is_all_str(
        self,
        items: list[uuid.UUID] | list[str] | SelectOfScalar[File],
    ) -> TypeIs[list[str]]:
        """Check if the list is all UUIDs or all strings."""
        if isinstance(items, SelectOfScalar):
            return False
        return all(isinstance(item, str) for item in items)

    def preload_files(
        self,
        identifiers: list[uuid.UUID] | list[str] | str | uuid.UUID,
    ) -> Sequence[File]:
        """Preload a file by id or key."""
        if isinstance(identifiers, (str)):
            identifiers = [identifiers]
        if isinstance(identifiers, (uuid.UUID)):
            identifiers = [identifiers]

        if self.list_is_all_uuids(identifiers):
            statement = select(File).where(
                File.plugin == self.plugin,
                col(File.id).in_(identifiers),
            )

        elif self.list_is_all_str(identifiers):
            statement = select(File).where(
                File.plugin == self.plugin,
                col(File.key).in_(identifiers),
            )
        else:
            msg = "Identifiers must be all UUIDs or all strings."
            raise ValueError(msg)

        files = self.db.exec(statement).all()
        self._preload_cache.extend(files)
        return files

    # endregion

    # region Properties

    @property
    def _show_id(self) -> str:
        if not self.__show_id_value:
            msg = "Show ID has not been set yet."
            raise AttributeError(msg)

        return self.__show_id_value

    @_show_id.setter
    def _show_id(self, show_id: str | re.Match[str]) -> None:
        if self.__show_id_value:
            msg = "Show ID has already been set and cannot be changed."
            raise AttributeError(msg)

        self.__show_id_value = str(show_id)

    def _has_show_id(self) -> str | None:
        return self.__show_id_value

    @property
    def plugin(self) -> Plugin:
        if not self.__plugin_value:
            msg = "Plugin has not been set yet."
            raise AttributeError(msg)

        return self.__plugin_value

    @plugin.setter
    def plugin(self, plugin: Plugin | None) -> None:
        if self.__plugin_value and not plugin:
            msg = "Plugin has already been set and cannot be set to None."
            raise AttributeError(msg)
        self.__plugin_value = plugin

    def _has_plugin(self) -> Plugin | None:
        return self.__plugin_value

    # endregion

    # region File Getters

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _source_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile]:  # noqa: ANN401
        """Returns the files required to detect changes to a show."""
        return []

    # ANN401 - This is a abstractmethod, it's fine to allow any as the implementation
    # can choose what the args and kwargs are.
    def _show_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile]:  # noqa: ANN401
        """Returns the files required to detect changes to a show."""
        return []

    # ANN401 - This is a abstractmethod, it's fine to allow any as the implementation
    # can choose what the args and kwargs are.
    def _season_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile]:  # noqa: ANN401
        """Returns the files required to detect changes to a season."""
        return []

    # ANN401 - This is a abstractmethod, it's fine to allow any as the implementation
    # can choose what the args and kwargs are.
    def _episode_files(self, *_args: Any, **_kwargs: Any) -> Sequence[BaseFile]:  # noqa: ANN401
        """Returns the files required to detect changes to an episode."""
        return []

    # endregion

    # region Timestamps

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _source_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the source files."""
        return self._oldest_file_timestamp(self._source_files(*_args, **_kwargs))

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _show_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the show files."""
        return self._oldest_file_timestamp(self._show_files(*_args, **_kwargs))

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _season_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the season files."""
        return self._oldest_file_timestamp(self._season_files(*_args, **_kwargs))

    # ANN401 - This is a abstractmethod, it's fine to allow Any as the implementation
    # can choose what the args and kwargs are.
    def _episode_timestamp(self, *_args: Any, **_kwargs: Any) -> datetime:  # noqa: ANN401
        """Get the oldest data_timestamp from the episode files."""
        return self._oldest_file_timestamp(self._episode_files(*_args, **_kwargs))

    # endregion

    # region URL

    @classmethod
    @cache
    @override
    def is_valid_url_format(cls, url: str) -> bool:
        return re.match(cls._url_regex(), url) is not None

    @classmethod
    @cache
    @abstractmethod
    def _url_regex(cls) -> str:
        """Returns the regex string to check if a URL is supported by the plugin."""

    @classmethod
    @cache
    @abstractmethod
    def domains(cls) -> list[str]:
        """Returns a list of the domains the plugin supports.

        The first domain should be the primary domain used by self.base_url().

        The domains should be in the format of example.com
        """
        # This is used in tests to make sure the regex supports every domain.

    @classmethod
    @cache
    def _domain(cls) -> str:
        """Returns the first domain the plugin supports."""
        return cls.domains()[0]

    @classmethod
    @cache
    def _base_url(cls) -> str:
        """Returns the base URL for the source.

        The base url is in the format of https://www.example.com/
        """
        return f"https://www.{cls._domain()}/"

    @classmethod
    @cache
    def _domain_regex(cls) -> str:
        """Returns a regex string that matches all of the source's domains."""
        if len(cls.domains()) > 1:
            escaped_domains = [cls._escape_domain(domain) for domain in cls.domains()]
            return "(?:" + "|".join(escaped_domains) + ")"

        return cls._escape_domain(cls._domain())

    @classmethod
    @cache
    def _escape_domain(cls, domain: str) -> str:
        """Escapes a plain text domain in the format of example.com.

        The escaping process will make a regex that matches the following:
        - example.com
        - www.example.com
        - http://example.com
        - http://www.example.com
        - https://www.example.com
        - https://example.com
        """
        return rf"(?:^(?:https?:\/\/)?(?:www\.)?{re.escape(domain)})"

    # endregion

    # region Watch Import Helpers

    def _get_episodes_by_id(self, episode_keys: list[str]) -> dict[str, Episode]:
        """Load episodes by their keys, scoped to this plugin."""
        if not episode_keys:
            return {}
        statement = (
            select(Episode)
            .join(Season)
            .join(Show)
            .join(Source)
            .where(Source.plugin_id == self.plugin.id)
            .where(col(Episode.key).in_(episode_keys))
        )
        return {episode.key: episode for episode in self.db.exec(statement)}

    def _get_watched_episode_dates(
        self,
        user: User,
        episodes_by_key: dict[str, Episode],
    ) -> dict[str, list[datetime]]:
        """Load watched dates grouped by episode ID."""
        if not episodes_by_key:
            return {}
        statement = select(EpisodeWatch.episode_id, EpisodeWatch.watch_date).where(
            EpisodeWatch.user_id == user.id,
            EpisodeWatch.episode_id.in_(  # type: ignore[union-attr]
                [episode.id for episode in episodes_by_key.values()],
            ),
        )
        result: dict[str, list[datetime]] = defaultdict(list)
        for episode_id, watch_date in self.db.exec(statement):
            result[str(episode_id)].append(watch_date)
        return result

    # endregion

    # region Other

    def _oldest_file_timestamp(self, files: Sequence[BaseFile]) -> datetime:
        return min(file.get_file_data_timestamp() for file in files)

    @classmethod
    @cache
    @override
    def plugin_id(cls) -> str:
        # TODO: Update name to ryn.cx to StreamChanneler.
        return f"ryn.cx-{cls._plugin_name()}"

    @classmethod
    @cache
    def _plugin_name(cls) -> str:
        """Returns the name of the plugin."""
        return cls.__name__

    def _get_cached_file[K, T](
        self,
        cache: dict[K, T],
        key: K,
        factory: Callable[[], T],
    ) -> T:
        """Generic helper to get or create cached file objects."""
        if key not in cache:
            cache[key] = factory()
        return cache[key]

    def _pretty_show_name(self) -> str:
        """Get a pretty name for the show if available."""
        source = Source.get_from_memory(self.db, self.plugin, self._plugin_name())
        if not source:
            return self._show_id

        if show := Show.get_from_memory(self.db, source, self._show_id):
            return show.name

        return self._show_id

    # TODO: Better name for this function?
    def _is_valid_url(self, file: BaseFile[Any], url: str) -> None:
        """Validates that the URL content is valid for the plugin.

        Raises InvalidURLError if the URL content is not valid.

        This is used to detect failed downloads
        """
        if not file.has_file_content():
            msg = f"Invalid {self._plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

    # endregion
