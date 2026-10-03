# TODO: Validate
import uuid

from sqlmodel import Field, Index, PrimaryKeyConstraint, Relationship, SQLModel

from app.episodes.models import Episode
from app.models import TimestampIdAndHashMixin
from app.titles.models import Title


# TODO: Validate
class BaseTmdbEpisodeOrder(SQLModel):
    tmdb_group_id: str = Field()
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    type: int | None = Field(default=None)
    group_count: int | None = Field(default=None)
    episode_count: int | None = Field(default=None)


# TODO: Validate
class TmdbEpisodeOrder(BaseTmdbEpisodeOrder, TimestampIdAndHashMixin, table=True):
    __table_args__ = (PrimaryKeyConstraint("tmdb_title_id", "tmdb_group_id"),)

    tmdb_title_id: uuid.UUID = Field(foreign_key="title.id", ondelete="CASCADE")
    tmdb_title: Title = Relationship()

    groups: list[TmdbEpisodeOrderGroup] = Relationship(
        back_populates="order",
        cascade_delete=True,
    )


# TODO: Validate
class BaseTmdbEpisodeOrderGroup(SQLModel):
    group_index: int = Field()
    name: str | None = Field(default=None)


# TODO: Validate
class TmdbEpisodeOrderGroup(
    BaseTmdbEpisodeOrderGroup,
    TimestampIdAndHashMixin,
    table=True,
):
    __table_args__ = (PrimaryKeyConstraint("order_id", "group_index"),)

    order_id: uuid.UUID = Field(
        foreign_key="tmdbepisodeorder.id",
        ondelete="CASCADE",
    )
    order: TmdbEpisodeOrder = Relationship(back_populates="groups")

    entries: list[TmdbEpisodeOrderEntry] = Relationship(
        back_populates="group",
        cascade_delete=True,
    )


# TODO: Validate
class BaseTmdbEpisodeOrderEntry(SQLModel):
    episode_number: int | None = Field(default=None)
    sort_order: int = Field()


# TODO: Validate
class TmdbEpisodeOrderEntry(
    BaseTmdbEpisodeOrderEntry,
    TimestampIdAndHashMixin,
    table=True,
):
    __table_args__ = (
        PrimaryKeyConstraint("order_id", "tmdb_episode_id"),
        Index("TmdbEpisodeOrderEntry-tmdb_episode_id-index", "tmdb_episode_id"),
        Index(
            "TmdbEpisodeOrderEntry-group_id-sort_order-index",
            "group_id",
            "sort_order",
        ),
    )

    order_id: uuid.UUID = Field(
        foreign_key="tmdbepisodeorder.id",
        ondelete="CASCADE",
    )

    group_id: uuid.UUID = Field(
        foreign_key="tmdbepisodeordergroup.id",
        ondelete="CASCADE",
    )
    group: TmdbEpisodeOrderGroup = Relationship(back_populates="entries")

    tmdb_episode_id: uuid.UUID = Field(
        foreign_key="episode.id",
        ondelete="CASCADE",
    )
    tmdb_episode: Episode = Relationship()
