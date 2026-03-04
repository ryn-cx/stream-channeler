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
from app.watches.models import BaseEpisodeWatch


class EpisodeWatchPostInput(SQLModel):
    episode_id: uuid.UUID
    watch_date: datetime = Field(default_factory=tz_datetime.now)
    verified: bool = False


class EpisodeWatchPatchInput(SQLModel):
    watch_date: datetime | None = None
    verified: bool | None = None


# TODO: Slim down this schema to just what is needed
class SingleEpisodeWatchOutput(BaseEpisodeWatch):
    id: uuid.UUID
    episode: EpisodeOutput
    season: SeasonOutput
    show: ShowOutput
    source: SourceOutput
    plugin: PluginOutput
    # reportGeneralTypeIssues - This field has a default value in the model, but no
    # default in the schema. This is acceptable because the input to the schema will
    # always be that model so it will always have a value.
    watch_date: datetime  # pyright: ignore[reportGeneralTypeIssues]


class EpisodeWatchItem(BaseEpisodeWatch):
    id: uuid.UUID
    episode_id: uuid.UUID
    # Fields with default values are marked as optional, but the value will always be
    # present so they need to be overridden.
    watch_date: datetime  # pyright: ignore[reportGeneralTypeIssues]
    verified: bool  # pyright: ignore[reportGeneralTypeIssues]


class WatchedEpisodesOutput(SQLModel):
    watches: list[EpisodeWatchItem] = Field()
    episodes: dict[uuid.UUID, EpisodeOutput] = Field()
    seasons: dict[uuid.UUID, SeasonOutput] = Field()
    shows: dict[uuid.UUID, ShowOutput] = Field()
    sources: dict[uuid.UUID, SourceOutput] = Field()
    plugins: dict[uuid.UUID, PluginOutput] = Field()
    count: int = Field()


class WatchImportFormatInformation(BaseModel):
    """Information about a supported watch import format."""

    plugin_id: str
    plugin_name: str
    file_type: str
    file_extension: str
    instructions: str


class WatchImportEntry(BaseModel):
    """A single entry from a watch history import."""

    show: str
    show_url: str
    episode: str
    episode_url: str


class WatchImportResult(BaseModel):
    """Result of a watch history import operation."""

    added: list[WatchImportEntry]
    existing: list[WatchImportEntry]
    skipped: list[WatchImportEntry]


class WatchImportInput(BaseModel):
    """Input parameters for a watch history import."""

    plugin_id: str
    new_only: bool
    verified: bool


class WatchImportPluginsOutput(BaseModel):
    """Response listing all plugins that support watch history import."""

    plugins: list[WatchImportFormatInformation]
