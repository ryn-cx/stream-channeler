# TODO: Validate
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.episodes.schemas import EpisodeOutput
from app.plugins.schemas import PluginOutput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowOutput
from app.sources.schemas import SourceOutput
from app.utils import tz_datetime
from app.watches.models import BaseWatch


class WatchPostInput(SQLModel):
    watch_date: datetime = Field(default_factory=tz_datetime.now)
    verified: bool = False


class WatchCreateInput(WatchPostInput):
    user_id: uuid.UUID


class WatchPatchInput(SQLModel):
    watch_date: datetime | None = None
    verified: bool | None = None


class WatchOutput(BaseWatch):
    id: uuid.UUID
    episode_id: uuid.UUID
    user_id: uuid.UUID
    # reportGeneralTypeIssues - Fields with default values are marked as optional, but
    # the value will always be present so they need to be overridden.
    watch_date: datetime  # pyright: ignore[reportGeneralTypeIssues]
    verified: bool  # pyright: ignore[reportGeneralTypeIssues]


class WatchItem(BaseWatch):
    id: uuid.UUID
    episode_id: uuid.UUID

    def __hash__(self) -> int:
        return hash(self.id)

    # reportGeneralTypeIssues - Fields with default values are marked as optional, but
    # the value will always be present so they need to be overridden.
    watch_date: datetime  # pyright: ignore[reportGeneralTypeIssues]
    verified: bool  # pyright: ignore[reportGeneralTypeIssues]


# TODO: This includes a lot of unused data.
class WatchesListOutput(SQLModel):
    watches: list[WatchItem] = Field()
    episodes: dict[uuid.UUID, EpisodeOutput] = Field()
    seasons: dict[uuid.UUID, SeasonOutput] = Field()
    shows: dict[uuid.UUID, ShowOutput] = Field()
    sources: dict[uuid.UUID, SourceOutput] = Field()
    plugins: dict[uuid.UUID, PluginOutput] = Field()


class WatchImportFormatInformation(BaseModel):
    plugin_id: str
    plugin_name: str
    file_type: str
    file_extension: str
    instructions: str


class WatchImportEntry(BaseModel):
    show: str
    show_url: str
    episode: str
    episode_url: str


class WatchImportResult(BaseModel):
    added: list[WatchImportEntry]
    existing: list[WatchImportEntry]
    skipped: list[WatchImportEntry]


class WatchImportInput(BaseModel):
    plugin_id: str
    new_only: bool
    verified: bool


class WatchImportPluginsOutput(BaseModel):
    plugins: list[WatchImportFormatInformation]
