# TODO: Validate
# General notes about the structure of the database:
# - The database is set up using a dual key setup.
#   - All tables have an automatically generated surrogate key named id. Any column
#     that refers to this id is named *_id.
#   - All tables have natural IDs named *_key that will be paired with the parent *_id
#     value to form a unique composite constraint. The only exception is Plugin because
#     it is the root of the hierarchy and does not have a parent.
#   - This structure allows each plugin to work in its own space in the database and
#     makes it impossible for two plugins to have any conflicts with each other due to
#     overlapping identifiers.
# state.
import uuid
from abc import ABC
from collections.abc import Sequence
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, override

from sqlalchemy import util
from sqlmodel import (
    DateTime,
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
)

from app.models import TimestampIdMixin
from app.users.models import User
from app.utils import tz_datetime

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.channels.models import (
        ChannelEpisodeWhiteList,
        ChannelSeasonWhiteList,
        ChannelShow,
    )


class BaseMetadataMixin(SQLModel):
    key: str = Field()

    # data_timestamp is similar to modified_at but with a few key differences. This will
    # track the timestamp of the data that the entry contains.
    # On a File, this is used to track the exact timestamp that the file was
    # downloaded. If another value in the file is modified updated_at will
    # automatically change, but data_timestamp will stay the same until the file is
    # updated. On a show the value should match the value of the data_timestamp of the
    # file used to obtain this information. This allows tracking the actual date of the
    # data instead of the date it was last modified in the database.
    # call-overload - See created_at for an explanation.
    data_timestamp: datetime | None = Field(
        sa_type=DateTime(timezone=True),
        default=None,
    )  # type: ignore[call-overload]
    update_at: datetime | None = Field(sa_type=DateTime(timezone=True), default=None)  # type: ignore[call-overload]
    deleted_at: datetime | None = Field(sa_type=DateTime(timezone=True), default=None)  # type: ignore[call-overload]

    # This is an optional field that can store anything that does not fit in the other
    # available fields. It will only ever be used by plugins, and allows plugins to
    # store extra information without needing to modify the database schema.
    extra: str | None = Field(default=None)

    def set_update_at(self, update_at: datetime | None) -> None:
        """Validate and set the update_at field.

        Validation will make sure that the update_at field is never incremented because
        updates should occur as soon as possible and there is almost never a reason to
        delay an update further into the future.

        Even if datetime is None this will still set update_at to None is the
        data_timestamp is newer than the existing update_at value.
        """
        # If the existing update_at value is newer than the data_timestamp, it has
        # already been used and can be cleared.
        if (
            self.update_at
            and self.data_timestamp
            and self.update_at < self.data_timestamp
        ):
            self.update_at = None

        # If update_at is not set nothing else needs to be done.
        if not update_at:
            return

        # If the existing data is newer than the new update_at value then the new
        # update_at can be ignored because the data is already up to date.
        if self.data_timestamp and self.data_timestamp >= update_at:
            return

        #  If the new date is before the existing date the existing date should be
        #  updated so the update happens as soon as possible.
        if self.update_at is None or update_at < self.update_at:
            self.update_at = update_at


class MetadataMixin(TimestampIdMixin, BaseMetadataMixin, ABC):
    def children(self) -> list[Source] | list[Show] | list[Season] | list[Episode]:
        """Return the direct children of the entry.

        Parent list: Plugin > Source > Show > Season > Episode

        Files are intentionally excluded from the children because they are not part of
        the direct media hierarchy.

        This is used for all recursive operations.
        """
        # Default value used by episodes because episodes have no children.
        return []

    def soft_delete(
        self,
        timestamp: datetime | None = None,
        *,
        recursive: bool = True,
    ) -> None:
        """Soft delete the entry.

        If it has already been deleted, the existing deleted_at value will be kept.
        """
        if self.deleted_at is None:
            self.deleted_at = timestamp or tz_datetime.now()

        if recursive:
            for child in self.children():
                child.soft_delete(timestamp)

    def soft_undelete(self, *, recursive: bool = True) -> None:
        """Undelete the entry by setting the deleted_at value to None."""
        self.deleted_at = None
        if recursive:
            for child in self.children():
                child.soft_undelete()

    def parent(self) -> Plugin | Source | Show | Season | None:
        """Return the parent of the entry."""
        # Default to having no parent and let subclasses override this method.
        return None


class BasePlugin(BaseMetadataMixin):
    name: str | None = Field(default=None)


class Plugin(BasePlugin, MetadataMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("key"),
        # Deleted filtering
        Index("Plugin-deleted_at-index", "deleted_at"),
    )

    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="CASCADE",
    )
    user: User | None = Relationship(
        back_populates="plugins",
    )

    sources: list[Source] = Relationship(
        back_populates="plugin",
        cascade_delete=True,
    )
    files: list[File] = Relationship(
        back_populates="plugin",
        cascade_delete=True,
    )

    @override
    def children(self) -> list[Source]:
        return self.sources

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        plugin_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Plugin | None:
        """Wrap `db.get(Plugin, ...)` for easier use.

        Args:
            db: Database session.
            plugin_key: Unique ID of the plugin.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Plugin instance if Plugin is found.
            - None if no Plugin is found.

        """
        return db.get(
            Plugin,
            plugin_key,
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        plugin_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Plugin:
        """Wrap `db.get_one(Plugin, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            plugin_key: Unique ID of the plugin.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Plugin instance

        Raises:
            NoResultFound: If no plugin with the given ID exists

        """
        return db.get_one(
            Plugin,
            plugin_key,
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(cls, db: Session, plugin_key: str) -> Plugin | None:
        """Like Plugin.get but will only return a Plugin if it is found in memory.

        Args:
            db: Database session
            plugin_key: Unique ID of the plugin

        Returns:
            Plugin instance if found in memory, None otherwise

        """
        return db.identity_map.get((Plugin, (plugin_key,), None))

    @classmethod
    def get_one_from_memory(cls, db: Session, plugin_key: str) -> Plugin:
        """Like Plugin.get_one but will only return a Plugin if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            plugin_key: Unique ID of the plugin

        Returns:
            Plugin instance

        Raises:
            KeyError: If no plugin with the given ID exists in memory

        """
        return db.identity_map[(Plugin, (plugin_key,), None)]

    def __str__(self) -> str:
        return f"Plugin: {self.name} ({self.key}) ({self.id})"


class BaseFile(BaseMetadataMixin):
    content: str | None = Field(default=None)


class File(BaseFile, MetadataMixin, table=True):
    __table_args__ = (PrimaryKeyConstraint("plugin_id", "key"),)

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(
        back_populates="files",
    )

    def parent(self) -> Plugin:
        return self.plugin

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        plugin: Plugin,
        file_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> File | None:
        """Wrap `db.get(File, ...)` for easier use.

        Args:
            db: Database session.
            plugin: Parent plugin instance.
            file_key: Unique ID of the file within the plugin.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - File instance if File is found.
            - None if no File is found.

        """
        return db.get(
            File,
            (plugin.id, file_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        plugin: Plugin,
        file_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> File:
        """Wrap `db.get_one(File, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            plugin: Parent plugin instance.
            file_key: Unique ID of the file within the plugin.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            File instance

        Raises:
            NoResultFound: If no file with the given ID exists in the plugin

        """
        return db.get_one(
            File,
            (plugin.id, file_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(
        cls,
        db: Session,
        plugin: Plugin,
        file_key: str,
    ) -> File | None:
        """Like File.get but will only return a File if it is found in memory.

        Args:
            db: Database session
            plugin: Parent plugin instance
            file_key: Unique ID of the file within the plugin

        Returns:
            File instance if found in memory, None otherwise

        """
        return db.identity_map.get((File, (plugin.id, file_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        plugin: Plugin,
        file_key: str,
    ) -> File:
        """Like File.get_one but will only return a File if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            plugin: Parent plugin instance
            file_key: Unique ID of the file within the plugin

        Returns:
            File instance

        Raises:
            KeyError: If no file with the given ID exists in memory

        """
        return db.identity_map[(File, (plugin.id, file_key), None)]

    def __str__(self) -> str:
        return f"{self.plugin}\nFile: {self.key} ({self.id})"


class BaseSource(BaseMetadataMixin):
    name: str | None = Field(default=None)
    favicon_url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


class Source(BaseSource, MetadataMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "key"),
        # User can choose this as a sorting option
        Index("Source-name-index", "name"),
    )

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")

    plugin: Plugin = Relationship(
        back_populates="sources",
    )

    def parent(self) -> Plugin:
        return self.plugin

    shows: list[Show] = Relationship(
        back_populates="source",
        cascade_delete=True,
    )

    @override
    def children(self) -> list[Show]:
        return self.shows

    def sorted_shows(self) -> list[Show]:
        """Get the shows sorted by name."""
        return sorted(self.shows, key=lambda show: (show.key, show.name))

    def __str__(self) -> str:
        return f"{self.plugin}\nSource: {self.name} ({self.key}) ({self.id})"

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        plugin: Plugin,
        source_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Source | None:
        """Wrap `db.get(Source, ...)` for easier use.

        Args:
            db: Database session.
            plugin: Parent plugin instance.
            source_key: Unique ID of the source within the plugin.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Source instance if Source is found.
            - None if no Source is found.

        """
        return db.get(
            Source,
            (plugin.id, source_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        plugin: Plugin,
        source_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Source:
        """Wrap `db.get_one(Source, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            plugin: Parent plugin instance.
            source_key: Unique ID of the source within the plugin.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Source instance

        Raises:
            NoResultFound: If no source with the given ID exists in the plugin

        """
        return db.get_one(
            Source,
            (plugin.id, source_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(
        cls,
        db: Session,
        plugin: Plugin,
        source_key: str,
    ) -> Source | None:
        """Like Source.get but will only return a Source if it is found in memory.

        Args:
            db: Database session
            plugin: Parent plugin instance
            source_key: Unique ID of the source within the plugin

        Returns:
            Source instance if found in memory, None otherwise

        """
        return db.identity_map.get((Source, (plugin.id, source_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        plugin: Plugin,
        source_key: str,
    ) -> Source:
        """Like Source.get_one but will only return a Source if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            plugin: Parent plugin instance
            source_key: Unique ID of the source within the plugin

        Returns:
            Source instance

        Raises:
            KeyError: If no source with the given ID exists in memory

        """
        return db.identity_map[(Source, (plugin.id, source_key), None)]


class BaseShow(BaseMetadataMixin):
    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


# The name "Show" was used instead of "Series" because it has a distinct singular and
# plural form and some people may use "Series" to refer to a "Season" so the word "Show"
# is less ambiguous and more flexible.
class Show(BaseShow, MetadataMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        # User can choose this as a sorting option
        Index("Show-name-index", "name"),
        Index("Show-media_type-index", "media_type"),
        # Deleted filtering
        Index("Show-deleted_at-index", "deleted_at"),
    )

    source_id: uuid.UUID = Field(foreign_key="source.id", ondelete="CASCADE")
    source: Source = Relationship(
        back_populates="shows",
    )

    def parent(self) -> Source:
        return self.source

    seasons: list[Season] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    channels: list[ChannelShow] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    @override
    def children(self) -> list[Season]:
        return self.seasons

    # TODO: Replace most usage of seasons with active_seasons
    # TODO: Something similar for episodes?
    def active_seasons(self) -> list[Season]:
        """Get the list of active (not soft-deleted) seasons."""
        return [season for season in self.seasons if season.deleted_at is None]

    def sorted_seasons(self) -> list[Season]:
        """Get the seasons sorted by sort_order and then by name."""
        return sorted(
            self.seasons,
            key=lambda season: (season.sort_order, season.name),
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        session: Session,
        source: Source,
        show_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Show | None:
        """Wrap `db.get(Show, ...)` for easier use.

        Args:
            session: Database session.
            source: Parent source instance.
            show_key: Unique ID of the show within the source.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Show instance if Show is found.
            - None if no Show is found.

        """
        return session.get(
            Show,
            (source.id, show_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        source: Source,
        show_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Show:
        """Wrap `db.get_one(Show, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            source: Parent source instance.
            show_key: Unique ID of the show within the source.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Show instance

        Raises:
            NoResultFound: If no show with the given ID exists in the source

        """
        return db.get_one(
            Show,
            (source.id, show_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(
        cls,
        db: Session,
        source: Source,
        show_key: str,
    ) -> Show | None:
        """Like Show.get but will only return a Show if it is found in memory.

        Args:
            db: Database session
            source: Parent source instance
            show_key: Unique ID of the show within the source

        Returns:
            Show instance if found in memory, None otherwise

        """
        return db.identity_map.get((Show, (source.id, show_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        source: Source,
        show_key: str,
    ) -> Show:
        """Like Show.get_one but will only return a Show if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            source: Parent source instance
            show_key: Unique ID of the show within the source

        Returns:
            Show instance

        Raises:
            KeyError: If no show with the given ID exists in memory

        """
        return db.identity_map[(Show, (source.id, show_key), None)]

    def __str__(self) -> str:
        return f"{self.source}\nShow: {self.name} ({self.key}) ({self.id})"


class BaseSeason(BaseMetadataMixin):
    sort_order: int | None = Field(default=None)
    name: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)


class Season(BaseSeason, MetadataMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        # User can choose this as a sorting option
        Index("Season-sort_order-index", "sort_order"),
        Index("Season-season_number-index", "season_number"),
        Index("Season-name-index", "name"),
        # Deleted filtering
        Index("Season-deleted_at-index", "deleted_at"),
    )

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(
        back_populates="seasons",
    )

    def parent(self) -> Show:
        return self.show

    episodes: list[Episode] = Relationship(
        back_populates="season",
        cascade_delete=True,
    )

    @override
    def children(self) -> list[Episode]:
        return self.episodes

    channel_white_list: list[ChannelSeasonWhiteList] = Relationship(
        back_populates="season",
        cascade_delete=True,
    )

    def sorted_episodes(self) -> list[Episode]:
        """Get the episodes sorted by sort_order and then by name."""
        return sorted(
            self.episodes,
            key=lambda episode: (episode.sort_order, episode.name),
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        show: Show,
        season_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Season | None:
        """Wrap `db.get(Season, ...)` for easier use.

        Args:
            db: Database session.
            show: Parent show instance.
            season_key: Unique ID of the season within the show.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Season instance if Season is found.
            - None if no Season is found.

        """
        return db.get(
            Season,
            (show.id, season_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        show: Show,
        season_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Season:
        """Wrap `db.get_one(Season, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            show: Parent show instance.
            season_key: Unique ID of the season within the show.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Season instance

        Raises:
            NoResultFound: If no season with the given ID exists in the show

        """
        return db.get_one(
            Season,
            (show.id, season_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(
        cls,
        db: Session,
        show: Show,
        season_key: str,
    ) -> Season | None:
        """Like Season.get but will only return a Season if it is found in memory.

        Args:
            db: Database session
            show: Parent show instance
            season_key: Unique ID of the season within the show

        Returns:
            Season instance if found in memory, None otherwise

        """
        return db.identity_map.get((Season, (show.id, season_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        show: Show,
        season_key: str,
    ) -> Season:
        """Like Season.get_one but will only return a Season if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            show: Parent show instance
            season_key: Unique ID of the season within the show

        Returns:
            Season instance

        Raises:
            KeyError: If no season with the given ID exists in memory

        """
        return db.identity_map[(Season, (show.id, season_key), None)]

    def __str__(self) -> str:
        if self.season_number:
            return f"{self.show}\nSeason {self.season_number}: {self.name} ({self.key}) ({self.id})"
        return f"{self.show}\nSeason: {self.name} ({self.key}) ({self.id})"


class BaseEpisode(BaseMetadataMixin):
    url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    name: str | None = Field(default=None)
    # call-overload - See created_at for an explanation.
    # These fields needs to be dates instead of datetimes to support old media.
    release_date: date | None = Field(default=None)  # pyright: ignore[reportArgumentType]
    air_date: date | None = Field(default=None)  # pyright: ignore[reportArgumentType]
    duration: int | None = Field(ge=0, default=None)


class Episode(BaseEpisode, MetadataMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        # User can choose this as a sorting option
        Index("Episode-sort_order-index", "sort_order"),
        Index("Episode-episode_number-index", "episode_number"),
        Index("Episode-name-index", "name"),
        Index("Episode-release_date-index", "release_date"),
        Index("Episode-air_date-index", "air_date"),
        Index("Episode-duration-index", "duration"),
        # Deleted filtering
        Index("Episode-deleted_at-index", "deleted_at"),
    )

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(
        back_populates="episodes",
    )

    def parent(self) -> Season:
        return self.season

    channel_white_list: list[ChannelEpisodeWhiteList] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )
    watched_by: list[EpisodeWatch] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get(  # noqa: PLR0913
        cls,
        db: Session,
        season: Season,
        episode_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Episode | None:
        """Wrap `db.get(Episode, ...)` for easier use.

        Args:
            db: Database session.
            season: Parent season instance.
            episode_key: Unique ID of the episode within the season.
            options: Passed directly to ``db.get``.
            populate_existing: Passed directly to ``db.get``.
            with_for_update: Passed directly to ``db.get``.
            identity_token: Passed directly to ``db.get``.
            execution_options: Passed directly to ``db.get``.
            bind_arguments: Passed directly to ``db.get``.

        Returns:
            - Episode instance if Episode is found.
            - None if no Episode is found.

        """
        return db.get(
            Episode,
            (season.id, episode_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_from_memory(
        cls,
        db: Session,
        season: Season,
        episode_key: str,
    ) -> Episode | None:
        """Like Episode.get but will only return a Episode if it is found in memory.

        Args:
            db: Database session
            season: Parent season instance
            episode_key: Unique ID of the episode within the season

        Returns:
            Episode instance if found in memory, None otherwise

        """
        return db.identity_map.get((Episode, (season.id, episode_key), None))

    @classmethod
    def get_one_from_memory(
        cls,
        db: Session,
        season: Season,
        episode_key: str,
    ) -> Episode:
        """Like Episode.get_one but will only return a Episode if it is found in memory.

        Raises an exception if no match is found.

        Args:
            db: Database session
            season: Parent season instance
            episode_key: Unique ID of the episode within the season

        Returns:
            Episode instance

        Raises:
            KeyError: If no episode with the given ID exists in memory

        """
        return db.identity_map[(Episode, (season.id, episode_key), None)]

    @classmethod
    # PLR0913 - Parameters are copied from the wrapped function.
    def get_one(  # noqa: PLR0913
        cls,
        db: Session,
        season: Season,
        episode_key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        # ANN401 - Parameter copied from the wrapped function.
        identity_token: Any | None = None,  # noqa: ANN401
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Episode:
        """Wrap `db.get_one(Episode, ...)` for easier use.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            season: Parent season instance.
            episode_key: Unique ID of the episode within the season.
            options: Passed directly to ``db.get_one``.
            populate_existing: Passed directly to ``db.get_one``.
            with_for_update: Passed directly to ``db.get_one``.
            identity_token: Passed directly to ``db.get_one``.
            execution_options: Passed directly to ``db.get_one``.
            bind_arguments: Passed directly to ``db.get_one``.

        Returns:
            Episode instance

        Raises:
            NoResultFound: If no episode with the given ID exists in the season

        """
        return db.get_one(
            Episode,
            (season.id, episode_key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    def __str__(self) -> str:
        if self.episode_number:
            return f"{self.season}\nEpisode {self.episode_number}: {self.name} ({self.key}) ({self.id})"

        return f"{self.season}\nEpisode: {self.name} ({self.key}) ({self.id})"


class BaseEpisodeWatch(SQLModel):
    # call-overload - See created_at for an explanation.
    watch_date: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        default_factory=tz_datetime.now,
    )

    verified: bool = Field(default=False)


class EpisodeWatch(TimestampIdMixin, BaseEpisodeWatch, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "episode_id", "watch_date"),
        # Used for filtering started shows
        Index("EpisodeWatch-user_id-episode_id-index", "user_id", "episode_id"),
        # Used for filtering watched episodes
        Index("EpisodeWatch-user_id-verified-index", "user_id", "verified"),
        # Used for filtering watched episodes by date
        Index("EpisodeWatch-watch_date-index", "watch_date"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(
        back_populates="watched_episodes",
    )

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    episode: Episode = Relationship(
        back_populates="watched_by",
    )
