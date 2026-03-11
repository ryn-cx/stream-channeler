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
from app.sources.models import Source

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.channels.models import ChannelShow
    from app.seasons.models import Season


class BaseShow(BaseMediaMixin):
    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


# The name "Show" was used instead of "Series" because it has a distinct singular and
# plural form and some people may use "Series" to refer to a "Season" so the word "Show"
# is less ambiguous and more flexible.
class Show(BaseShow, MediaMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        # Filtering options.
        Index("Show-name-index", "name"),
        Index("Show-media_type-index", "media_type"),
        # Deleted filtering.
        Index("Show-deleted_at-index", "deleted_at"),
    )

    source_id: uuid.UUID = Field(foreign_key="source.id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="shows")

    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id)
            .select_from(Source)
            .join(Plugin)
            .where(Source.id == self.source_id),
        ).first()

    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public)
                .select_from(Source)
                .join(Plugin)
                .where(Source.id == self.source_id),
            ).first(),
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
        base_show = "Show: "
        if self.name:
            base_show += f" {self.name}"
        if self.key:
            base_show += f" ({self.key})"
        if self.id:
            base_show += f" ({self.id})"
        return f"{self.source}\n{base_show}"
