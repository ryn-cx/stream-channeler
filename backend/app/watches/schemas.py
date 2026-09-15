# TODO: Validate
import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel

from app.episodes.schemas import EpisodeOutput
from app.plugins.schemas import PluginOutput
from app.schemas import (
    BaseInput,
    BaseUpdateWithoutKey,
    make_model_with_all_fields_optional,
)
from app.seasons.schemas import SeasonOutput
from app.sources.schemas import SourcePublic
from app.titles.schemas import TitlePublic
from app.watches.models import BaseWatch, Watch


# TODO: Validate
class WatchCreate(BaseInput, BaseWatch):
    """Schema for creating a `Watch`."""


# TODO: Validate
class WatchUpdate(
    make_model_with_all_fields_optional(BaseWatch),
    BaseUpdateWithoutKey[Watch],
):
    """Schema for updating a `Watch`."""


# TODO: This class may be redundant
# TODO: Validate
class WatchOutput(BaseWatch):
    """Schema for returning a `Watch`."""

    id: uuid.UUID
    episode_id: uuid.UUID | None
    watch_identifier: str
    user_id: uuid.UUID
    # reportGeneralTypeIssues - Fields with default values are marked as optional, but
    # the value will always be present so they need to be overridden.
    watch_date: datetime  # pyright: ignore[reportGeneralTypeIssues]
    verified: bool  # pyright: ignore[reportGeneralTypeIssues]


# TODO: Validate
class WatchItem(BaseWatch):
    id: uuid.UUID
    episode_id: uuid.UUID | None
    # The episode itself, which is what the watch counts for. The identifier is
    # episode that identifier resolved to here, and is what keys `episodes` on
    # the list output.
    watch_identifier: str
    tmdb_episode_id: uuid.UUID

    # TODO: Validate
    def __hash__(self) -> int:
        return hash(self.id)

    # reportGeneralTypeIssues - Fields with default values are marked as optional, but
    # the value will always be present so they need to be overridden.
    watch_date: datetime  # pyright: ignore[reportGeneralTypeIssues]
    verified: bool  # pyright: ignore[reportGeneralTypeIssues]


# TODO: This includes a lot of unused data.
# TODO: Validate
class WatchesListOutput(SQLModel):
    watches: list[WatchItem] = Field()
    episodes: dict[uuid.UUID, EpisodeOutput] = Field()
    seasons: dict[uuid.UUID, SeasonOutput] = Field()
    titles: dict[uuid.UUID, TitlePublic] = Field()
    sources: dict[uuid.UUID, SourcePublic] = Field()
    plugins: dict[uuid.UUID, PluginOutput] = Field()
    total_count: int = Field(default=0)
    filtered_count: int = Field(default=0)
    is_server_side: bool = Field(default=False)


# TODO: Validate
class WatchImportResult(BaseModel):
    title: str
    title_url: str
    episode: str
    episode_url: str


# TODO: Validate
class WatchImportResults(BaseModel):
    added: list[WatchImportResult]
    existing: list[WatchImportResult]
    skipped: list[WatchImportResult]


# TODO: Validate
class WatchRelinkResults(BaseModel):
    """What a relink run found and what it was able to attach.

    `detached` is every watch that had no episode when the run started, and
    `relinked` is how many of them a link to point at was found for. The rest
    name an episode this database does not currently carry a live link to.
    """

    detached: int
    relinked: int


# TODO: Validate
class WatchExportEntry(BaseModel):
    watch_identifier: str = PydanticField(
        validation_alias=AliasChoices("watch_identifier", "tmdb_episode_key"),
    )
    watch_date: datetime
    verified: bool | None = None


# TODO: Validate
class WatchImportInput(BaseInput):
    plugin_key: str
    new_only: bool
    verified: bool
