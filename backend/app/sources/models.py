import uuid
from collections.abc import Sequence
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

from app.models import BaseMediaMixin, MediaMixin
from app.plugins.models import Plugin

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.shows.models import Show


class BaseSource(BaseMediaMixin):
    name: str | None = Field(default=None)
    favicon_url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


class Source(BaseSource, MediaMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "key"),
        UniqueConstraint("id"),
        # Filtering options.
        Index("Source-name-index", "name"),
        # Deleted filtering.
        Index("Source-deleted_at-index", "deleted_at"),
    )

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(back_populates="sources")
    shows: list[Show] = Relationship(back_populates="source", cascade_delete=True)

    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id).where(Plugin.id == self.plugin_id),
        ).first()

    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public).where(Plugin.id == self.plugin_id),
            ).first(),
        )

    @override
    def parent(self) -> Plugin:
        return self.plugin

    @override
    def children(self) -> list[Show]:
        return self.shows

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

    def __str__(self) -> str:
        base_source = "Source: "
        if self.name:
            base_source += f" {self.name}"
        if self.key:
            base_source += f" ({self.key})"
        if self.id:
            base_source += f" ({self.id})"
        return f"{self.plugin}\n{base_source}"
