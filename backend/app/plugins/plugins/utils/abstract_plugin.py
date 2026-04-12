# TODO: Validate
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, Field

from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.manage_plugins import register_plugins
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.watches.schemas import WatchImportResults

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.users.models import User


class AbstractPlugin(ABC):
    """Abstract class that must be implemented by plugins for them to function."""

    # region Abstract methods

    @classmethod
    @abstractmethod
    def plugin_key(cls) -> str:
        """The unique identifier for the plugin.

        This is used to match Plugin records in the database with the actual plugins.

        Returns:
            The unique identifier for the plugin.
        """

    @classmethod
    @abstractmethod
    def is_valid_url_format(cls, url: str) -> bool:
        """Check if the given URL is supported by the plugin.

        This function should check the url to confirm it has the right format for the
        plugin. This should only check the format of the URL, it should not check if the
        URL is actually valid. If the URL is the correct format but it is not a valid
        URL InvalidURLError should be raised when import_url is called.

        Args:
            url: The URL to check.

        Returns:
            True if the URL is valid, False otherwise.
        """

    @abstractmethod
    def import_url(self, url: str) -> list[URLImportResult]:
        """Import a URL into the database.

        This function is only called after a URL is confirmed to be the correct format
        for the plugin using is_valid_url_format. It should take the URL and import all
        of the information from the URL into the database.

        Args:
            url: The URL to import.

        Returns:
            A list of URLImportResult based on the URL.
        """

    def update_show(self, show: Show) -> None:
        """Update an existing show in the database.

        Called when a show has an update_at value that is in the past. By default
        clears update_at so it is not retried.
        """
        show.update_at = None

    def update_season(self, season: Season) -> None:
        """Update an existing season in the database.

        Called when a season has an update_at value that is in the past. By default
        clears update_at so it is not retried.
        """
        season.update_at = None

    def update_episode(self, episode: Episode) -> None:
        """Update an existing episode in the database.

        Called when an episode has an update_at value that is in the past. By default
        clears update_at so it is not retried.
        """
        episode.update_at = None

    # B027 - These functions do not need to be implemented so they do not need the
    # @abstractmethod decorator.
    def initialize_plugin(self) -> None:  # noqa: B027
        """Run plugin-specific initialization.

        Called before import_url to allow plugins to set up any state that depends on
        existing files in the database (e.g. downloading provider metadata, initial
        browse files).
        """

    def update_plugin(self, plugin: Plugin) -> None:
        """Update an existing plugin in the database.

        Called when a plugin has an update_at value that is in the past. By default
        clears update_at so it is not retried.
        """
        plugin.update_at = None

    def update_file(self, file: File) -> None:
        """Update an existing file in the database.

        Called when a file has an update_at value that is in the past. By default
        clears update_at so it is not retried.
        """
        file.update_at = None

    def update_source(self, source: Source) -> None:
        """Update an existing source in the database.

        Called when a source has an update_at value that is in the past. By default
        clears update_at so it is not retried.
        """
        source.update_at = None

    supports_import_watch_history: bool = False
    import_watch_history_file_extension: str | None = None

    @classmethod
    def import_watch_history_instructions(cls) -> str:
        """Markdown instructions for how to import watch history.

        Only needs to be implemented if the plugin supports watch history import.
        """
        msg = "Watch history import is not supported by this plugin."
        raise NotImplementedError(msg)

    def import_watch_history(
        self,
        content: str,
        user: User,
        *,
        new_only: bool,
        verified: bool,
    ) -> WatchImportResults:
        """Import watch history from uploaded content.

        Only needs to be implemented if the plugin supports watch history import.

        Args:
            content: The raw file content uploaded by the user.
            user: The user performing the import.
            new_only: If True, skip episodes the user has already watched.
            verified: If True, mark imported watches as verified.

        Returns:
            A WatchImportResult results of the import.
        """
        msg = "Watch history import is not supported by this plugin."
        raise NotImplementedError(msg)

    # endregion

    # region URL Import Info

    supports_import_url: bool = False

    @classmethod
    def import_url_instructions(cls) -> str:
        """Markdown description of how URL importing works for this plugin.

        Should include example URLs. Only needs to be set if the plugin
        supports URL import.
        """
        return ""

    # endregion URL Import Info

    # region Search

    supports_search: bool = False

    def search(self, query: str) -> PluginSearchResults:
        """Search for shows/movies on this plugin's platform.

        Only needs to be implemented if the plugin supports searching.

        Args:
            query: The search string.

        Returns:
            Search results with metadata about source selection support.
        """
        msg = "Search is not supported by this plugin."
        raise NotImplementedError(msg)

    # endregion Search

    # region Magic methods

    @override
    def __init_subclass__(cls, *, register: bool = True, **kwargs: Any) -> None:
        # Any class that inherits from AbstractPlugin will be registered as a plugin.
        # If the class should not be registered, set register to False.

        # For example FakePlugin(AbstractPlugin, register=False) will not be
        # registered, but RealPlugin(AbstractPlugin) will be registered.
        super().__init_subclass__(**kwargs)
        if register:
            register_plugins(cls)

    @abstractmethod
    # PLR0913 - This function has extra parameters to give extra flexibility for plugin
    # developers.
    def __init__(  # noqa: PLR0913
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        """Initialize the Plugin.

        Args:
            db: The database session to use.
            url: The URL to import or update, only present when import_url is going to
            be called.
            source: The source to update, only present when update_source is going to be
            called.
            show: The show to update, only present when update_show is going to be called.
            season: The season to update, only present when update_season is going to be
            called.
            episode: The episode to update, only present when update_episode is going to
            be called.

        These arguements can be accessed on initialization, or accessed from the
        function that is being called. They are duplicated in both location to allow
        plugin developers to choose the most convenient way to access the data.
        """

    # endregion


class PluginSearchResultSource(BaseModel):
    """A streaming source available for a search result."""

    name: str
    icon_url: str | None = None


class PluginSearchResult(BaseModel):
    """A single result from a plugin search."""

    title: str
    url: str
    year: int | None = None
    image_url: str | None = None
    media_type: str | None = None
    sources: list[PluginSearchResultSource] = Field(default=[])


class PluginSearchResults(BaseModel):
    """Container for plugin search results."""

    has_source_selection: bool
    results: list[PluginSearchResult]


class InvalidURLError(Exception):
    """Exception raised when a URL is determined to be invalid while importing it."""


class URLImportResult(BaseModel):
    # Example outputs:

    #   If a user adds a URL for a show it is assumed the user wants every
    #   season/episode of that shows and all future episodes as well so the output
    #   should be:
    #       show=show - Show is always required
    #       whitelist_mode=False - New seasons/episodes should be added automatically.

    #   If the user adds a URL for a season it is assumed the user wants just the
    #   episodes from that season and all other seasons/episodes should be excluded so
    #   the output should be:
    #       show=show - Show is always required
    #       seasons=[season] - Just the imported season should be whitelisted.
    #       whitelist_mode=True - New seasons need to be manually whitelisted.

    # Let this be a Sequence because SQLModel defaults to Sequences.
    show: Show
    """The show that was imported from the URL."""

    # Let this be a Sequence because SQLModel defaults to Sequences.
    seasons: list[Season] = Field(default=[])
    """The seasons that should be added to the user's whitelist or blacklist."""
    episodes: list[Episode] = Field(default=[])
    """The episodes that should be added to the user's whitelist or blacklist."""

    whitelist_mode: bool = Field(default=False)
    """If True the media should be added in whitelist mode meaning that if a new
    season/episode is added in the future it will NOT automatically be added to a user's
    channel because the user has to manually whitelist new content that they want to
    include.

    If False the media will be added in blacklist mode meaning that if a new
    season/episode is added in the future it will automatically be added to a user's
    channel because the user has to manually blacklist new content that they want to
    exclude."""
