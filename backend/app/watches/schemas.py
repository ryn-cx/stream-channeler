# TODO: Validate
import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from app.episodes.schemas import EpisodeOutput
from app.plugins.schemas import PluginOutput
from app.schemas import BaseInput, BasePatchInputWithoutKey
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.watches.models import BaseWatch, Watch


class WatchPostInput(BaseInput, BaseWatch):
    pass


class WatchCreateInput(WatchPostInput):
    user_id: uuid.UUID


class WatchPatchInput(BasePatchInputWithoutKey[Watch], BaseWatch):
    watch_date: datetime | None = None  # type: ignore[assignment]
    verified: bool | None = None  # type: ignore[assignment]


# TODO: This class may be redundant
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
    shows: dict[uuid.UUID, ShowPublic] = Field()
    sources: dict[uuid.UUID, SourcePublic] = Field()
    plugins: dict[uuid.UUID, PluginOutput] = Field()


class WatchImportResult(BaseModel):
    show: str
    show_url: str
    episode: str
    episode_url: str


class WatchImportResults(BaseModel):
    added: list[WatchImportResult]
    existing: list[WatchImportResult]
    skipped: list[WatchImportResult]


class WatchImportInput(BaseInput):
    plugin_key: str
    new_only: bool
    verified: bool
