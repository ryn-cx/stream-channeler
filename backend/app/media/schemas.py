# TODO: Validate
import uuid
from datetime import date, datetime

from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel

from app.media.models import (
    BaseEpisode,
    BaseEpisodeWatch,
    BaseFile,
    BaseMetadataMixin,
    BasePlugin,
    BaseSeason,
    BaseShow,
    BaseSource,
    Episode,
    File,
    Plugin,
    Season,
    Show,
    Source,
)
from app.utils import tz_datetime

# region Upsert Inputs


class MetadataMixinInput[T: BaseMetadataMixin](BaseMetadataMixin):
    def _update_existing_entry(
        self,
        existing_entry: T,
        protected_keys: set[str],
    ) -> T:
        # This function will never directly set update_at to None because it is possible
        # that update_at is None because the value was not defined. However, the call to
        # set_update_at can set the value to None if the data_timestamp is newer than
        # the existing update_at value.

        # Never upsert the update_at value because it will be managed by the
        # set_update_at method which has additional logic to validate and set the value.
        protected_keys.add("update_at")

        dumped = self.model_dump(exclude=protected_keys)

        # Only update modified_at if actual content fields changed. Metadata fields
        # (key, data_timestamp, deleted_at) are excluded from change detection because
        # they are lifecycle/identity fields, not content.
        metadata_fields = {"key", "data_timestamp", "deleted_at"}
        has_changes = any(
            getattr(existing_entry, k) != v
            for k, v in dumped.items()
            if k not in metadata_fields
        )

        existing_entry.sqlmodel_update(dumped)
        existing_entry.set_update_at(self.update_at)

        if has_changes:
            existing_entry.modified_at = tz_datetime.now()

        return existing_entry

    def clean_protected_keys(
        self,
        protected_keys: set[str] | None,
    ) -> set[str]:
        if protected_keys is None:
            return set()
        return protected_keys


# These classes may seem redundant because SQLAlchemy has Session.merge and ORM "upsert"
# Statements, but these features where inadequate when working with models that have
# keys that are randomly generated.

# Session.merge was inadequate because it does not handle children of randomly generated
# keys well. For example, if you set create a new Plugin then set a Source to that
# plugin you will have Source.plugin_key set to a value that does not actually exist in
# the database and it will cause an error when trying to merge the data.

# ORM "upsert" Statements where inadequate because they do not give you an easy way to
# compare the new value with the existing value which is essential for making sure
# update_at values don't get changed in unexpected ways.

# The performance of these upsert methods are adequate, when benchmarked they where
# faster than Session.merge, and about equal to ORM "upsert" statements depending on the
# query size and number of values that where modified.

# Sources:
# https://docs.sqlalchemy.org/en/21/orm/session_state_management.html
# https://docs.sqlalchemy.org/en/21/orm/queryguide/dml.html#orm-queryguide-upsert


class PluginInput(BasePlugin, MetadataMixinInput[Plugin]):
    """Input schema for creating or updating a plugin."""

    user_id: uuid.UUID | None = None

    def upsert(
        self,
        db: Session,
        existing_plugin: Plugin | None,
        protected_keys: set[str] | None = None,
    ) -> Plugin:
        """Insert or update a plugin in the database.

        Args:
            db: Database session
            existing_plugin: Existing Plugin instance to update. If NOT_PROVIDED,
                will look up the plugin from the database using the key. If None,
                will create a new plugin.
            protected_keys: Keys that should not be updated if the plugin already
            exists.

        Returns:
            Plugin instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_plugin:
            return self._update_existing_entry(existing_plugin, protected_keys)

        plugin = Plugin.model_validate(self)
        db.add(plugin)
        return plugin


class FileInput(BaseFile, MetadataMixinInput[File]):
    """Input schema for creating or updating a file."""

    def upsert(
        self,
        plugin: Plugin,
        existing_file: File | None,
        protected_keys: set[str] | None = None,
    ) -> File:
        """Insert or update a file in the database.

        Args:
            db: Database session.
            plugin: Parent plugin instance.
            existing_file: Existing File instance to update. If NOT_PROVIDED,
                will look up the file from the database using the key. If None,
                will create a new file.
            protected_keys: Keys that should not be updated if the file already
            exists.

        Returns:
            File instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_file:
            return self._update_existing_entry(existing_file, protected_keys)

        file = File.model_validate(self, update={"plugin_id": plugin.id})
        plugin.files.append(file)
        # file.plugin = plugin
        return file


class SourceInput(BaseSource, MetadataMixinInput[Source]):
    """Input schema for creating or updating a source."""

    def upsert(
        self,
        plugin: Plugin,
        existing_source: Source | None,
        protected_keys: set[str] | None = None,
    ) -> Source:
        """Insert or update a source in the database.

        Args:
            plugin: Parent plugin instance.
            existing_source: Existing Source instance to update. If NOT_PROVIDED,
                will search through plugin.sources for a matching key. If None,
                will create a new source.
            protected_keys: Keys that should not be updated if the source already
            exists.

        Returns:
            Source instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_source:
            return self._update_existing_entry(existing_source, protected_keys)

        source = Source.model_validate(self, update={"plugin_id": plugin.id})
        plugin.sources.append(source)
        # source.plugin = plugin
        return source


class ShowInput(BaseShow, MetadataMixinInput[Show]):
    """Input schema for creating or updating a show."""

    def upsert(
        self,
        source: Source,
        existing_show: Show | None,
        protected_keys: set[str] | None = None,
    ) -> Show:
        """Insert or update a show in the database.

        Args:
            source: Parent source instance.
            existing_show: Existing Show instance to update. If NOT_PROVIDED,
                will search through source.shows for a matching key. If None,
                will create a new show.
            protected_keys: Keys that should not be updated if the show already
            exists.

        Returns:
            Show instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_show:
            return self._update_existing_entry(existing_show, protected_keys)

        show = Show.model_validate(self, update={"source_id": source.id})
        source.shows.append(show)
        # show.source = source
        return show


class SeasonInput(BaseSeason, MetadataMixinInput[Season]):
    """Input schema for creating or updating a season."""

    def upsert(
        self,
        show: Show,
        existing_season: Season | None,
        protected_keys: set[str] | None = None,
    ) -> Season:
        """Insert or update a season in the database.

        Args:
            show: Parent show instance.
            existing_season: Existing Season instance to update. If NOT_PROVIDED,
                will search through show.seasons for a matching key. If None,
                will create a new season.
            protected_keys: Keys that should not be updated if the season already
            exists.

        Returns:
            Season instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_season:
            return self._update_existing_entry(existing_season, protected_keys)

        season = Season.model_validate(self, update={"show_id": show.id})
        show.seasons.append(season)
        # season.show = show
        return season


class EpisodeInput(BaseEpisode, MetadataMixinInput[Episode]):
    """Input schema for creating or updating an episode."""

    def upsert(
        self,
        season: Season,
        existing_episode: Episode | None,
        protected_keys: set[str] | None = None,
    ) -> Episode:
        """Insert or update an episode in the database.

        Args:
            season: Parent season instance.
            existing_episode: Existing Episode instance to update. If NOT_PROVIDED,
                will search through season.episodes for a matching key. If None,
                will create a new episode.
            protected_keys: Keys that should not be updated if the episode already
            exists.

        Returns:
            Episode instance (either newly created or updated)
        """
        protected_keys = self.clean_protected_keys(protected_keys)

        if existing_episode:
            return self._update_existing_entry(existing_episode, protected_keys)

        episode = Episode.model_validate(self, update={"season_id": season.id})
        season.episodes.append(episode)
        # episode.season = season
        return episode


# endregion

# region Output


class PluginOutput(BasePlugin):
    id: uuid.UUID
    user_id: uuid.UUID | None = None


class SourceOutput(BaseSource):
    plugin_id: uuid.UUID
    id: uuid.UUID


class ShowOutput(BaseShow):
    source_id: uuid.UUID
    id: uuid.UUID


class SeasonOutput(BaseSeason):
    show_id: uuid.UUID
    id: uuid.UUID


class EpisodeOutput(BaseEpisode):
    season_id: uuid.UUID
    id: uuid.UUID


# endregion

# region List Output


class PluginsListOutput(BaseModel):
    data: list[PluginOutput]
    count: int


class SourcesListOutput(BaseModel):
    data: list[SourceOutput]
    count: int


class ShowsListOutput(BaseModel):
    data: list[ShowOutput]
    count: int


class SeasonsListOutput(BaseModel):
    data: list[SeasonOutput]
    count: int


class EpisodesListOutput(BaseModel):
    data: list[EpisodeOutput]
    count: int


# endregion

# region Post


class PluginPostInput(SQLModel):
    name: str | None = None
    data_timestamp: datetime | None = None


class SourcePostInput(BaseSource):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))  # pyright: ignore[reportIncompatibleVariableOverride]
    data_timestamp: datetime | None = None
    plugin_key: str


class ShowPostInput(BaseShow):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))  # pyright: ignore[reportIncompatibleVariableOverride]
    data_timestamp: datetime | None = None
    source_id: uuid.UUID


class SeasonPostInput(BaseSeason):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))  # pyright: ignore[reportIncompatibleVariableOverride]
    data_timestamp: datetime | None = None
    show_id: uuid.UUID


class EpisodePostInput(BaseEpisode):
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))  # pyright: ignore[reportIncompatibleVariableOverride]
    data_timestamp: datetime | None = None
    season_id: uuid.UUID


# endregion

# region Patch


class PluginPatchInput(SQLModel):
    name: str | None = None
    data_timestamp: datetime | None = None


class SourcePatchInput(SQLModel):
    name: str | None = None
    favicon_url: str | None = None
    image_url: str | None = None
    data_timestamp: datetime | None = None


class ShowPatchInput(SQLModel):
    name: str | None = None
    media_type: str | None = None
    description: str | None = None
    url: str | None = None
    image_url: str | None = None
    data_timestamp: datetime | None = None


class SeasonPatchInput(SQLModel):
    sort_order: int | None = None
    name: str | None = None
    url: str | None = None
    image_url: str | None = None
    season_number: int | None = None
    data_timestamp: datetime | None = None


class EpisodePatchInput(SQLModel):
    url: str | None = None
    sort_order: int | None = None
    description: str | None = None
    image_url: str | None = None
    episode_number: int | None = None
    name: str | None = None
    release_date: date | None = None
    air_date: date | None = None
    duration: int | None = Field(ge=0, default=None)
    data_timestamp: datetime | None = None


# endregion

# region Episode Watches


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


# endregion

# region Watch Import


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


# endregion
