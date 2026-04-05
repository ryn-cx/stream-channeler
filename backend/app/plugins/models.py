# TODO: Validate
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from sqlalchemy import util
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
)

from app.models import SA_TYPE, BaseMediaMixin, MediaMixin
from app.users.models import User

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.sources.models import Source


class BasePlugin(BaseMediaMixin):
    name: str | None = Field(default=None)
    version: str | None = Field(default=None)
    public: bool


class Plugin(BasePlugin, MediaMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint("user_id", "key"),
        # Deleted filtering.
        Index("Plugin-deleted_at-index", "deleted_at"),
    )

    user_id: uuid.UUID = Field(
        foreign_key="user.id",
        ondelete="CASCADE",
    )
    user: User = Relationship(back_populates="plugins")

    sources: list[Source] = Relationship(back_populates="plugin", cascade_delete=True)
    files: list[File] = Relationship(back_populates="plugin", cascade_delete=True)

    def parent(self) -> User:
        return self.user

    def get_user_id(self, _session: Session) -> uuid.UUID:
        return self.user_id

    def is_public(self, _session: Session) -> bool:
        return self.public

    @override
    def children(self) -> list[Source]:
        return self.sources

    def get_sibling(self, db: Session, key: str) -> Plugin | None:
        return Plugin.get(db, key, self.user)

    def __str__(self) -> str:
        base_plugin = "Plugin:"
        if self.key:
            base_plugin += f" {self.key}"
        if self.id:
            base_plugin += f" ({self.id})"
        return base_plugin

    @classmethod
    def get(
        cls,
        db: Session,
        plugin_key: str,
        user: User,
        *,
        options: Sequence[ORMOption] | None = None,
    ) -> Plugin | None:
        """Look up a Plugin by its unique key.

        Args:
            db: Database session.
            plugin_key: Unique key of the plugin.
            user: User to scope the lookup.
            options: SQLAlchemy ORM options (e.g. joinedload).

        Returns:
            Plugin instance if found, None otherwise.

        """
        statement = select(Plugin).where(
            Plugin.key == plugin_key,
            Plugin.user_id == user.id,
        )
        if options:
            statement = statement.options(*options)
        return db.exec(statement).first()

    @classmethod
    def get_one(
        cls,
        db: Session,
        plugin_key: str,
        user: User,
        *,
        options: Sequence[ORMOption] | None = None,
    ) -> Plugin:
        """Look up a Plugin by its unique key.

        Raises an exception if no match is found.

        Args:
            db: Database session.
            plugin_key: Unique key of the plugin.
            user: User to scope the lookup.
            options: SQLAlchemy ORM options (e.g. joinedload).

        Returns:
            Plugin instance.

        Raises:
            NoResultFound: If no plugin with the given key exists.

        """
        statement = select(Plugin).where(
            Plugin.key == plugin_key,
            Plugin.user_id == user.id,
        )
        if options:
            statement = statement.options(*options)
        return db.exec(statement).unique().one()


class BaseFile(BaseMediaMixin):
    data_timestamp: datetime = Field(sa_type=SA_TYPE)  # type: ignore[call-overload]
    content: str | None = Field(default=None)


class File(BaseFile, MediaMixin, table=True):
    __table_args__ = (PrimaryKeyConstraint("plugin_id", "key"),)

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(back_populates="files")

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
        base_file = "File:"
        if self.key:
            base_file += f" {self.key}"
        if self.id:
            base_file += f" ({self.id})"
        return f"{self.plugin}\n{base_file}"
