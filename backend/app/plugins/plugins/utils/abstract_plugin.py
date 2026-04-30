# TODO: Validate
from __future__ import annotations

import inspect
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
    """Base class every plugin must implement."""

    # region Abstract Methods
    @classmethod
    @abstractmethod
    def plugin_key(cls) -> str:
        """Unique identifier for the plugin.

        Used to match a ``Plugin (db)`` record with the actual ``Plugin (class)``.

        Returns:
            The unique identifier for the plugin.
        """

    @abstractmethod
    def __init__(self, session: Session) -> None:
        """Initialize the plugin class.

        The ``Plugin (class)`` needs to be able to interact with the database so the
        session should probably be saved to an instance variable like ``self.session =
        session``.

        Args:
            session: The database session.
        """

    # region Abstract Methods

    # region import_url

    @classmethod
    def is_valid_url_format(cls, url: str) -> bool:  # noqa: ARG003
        """Check if ``url`` has the right format for the plugin.

        Does NOT check if ``url`` is actually valid, this will be done by
        ``import_url``.

        Args:
            url: The URL to check.

        Returns:
            True if the URL is valid, False otherwise.
        """
        return False

    def import_url(self, url: str) -> list[URLImportResult]:
        """Import ``url`` into the database.

        Only called if ``is_valid_url_format`` returns ``True`` on the ``url``.

        Args:
            url: The URL to import.

        Returns:
            A list of ``URLImportResult``.

        Raises:
            ``InvalidURLError`` if the URL has the correct format but is not actually
            valid.
        """
        msg = "import_url is not supported by this plugin."
        raise NotImplementedError(msg)

    @classmethod
    def import_url_instructions(cls) -> str:
        """Markdown describing what URLs this plugin supports.

        Override to include example URLs so users know what to paste.
        """
        return "This plugin does not have specific URL import instructions."

    def update_plugin(self, plugin: Plugin) -> None:
        """Update an existing plugin in the database.

        Called when ``Plugin.update_at > datetime.now()``.

        By default this will clear ``Plugin.update_at``, override to implement `Plugin`
        specific update logic.

        Args:
            plugin: The ``Plugin`` to update.
        """
        plugin.update_at = None

    def update_source(self, source: Source) -> None:
        """Update an existing source in the database.

        Called when ``Source.update_at > datetime.now()``.

        By default this will clear ``Source.update_at``, override to implement ``Plugin``
        specific update logic.

        Args:
            source: The ``Source`` to update.
        """
        source.update_at = None

    def update_show(self, show: Show) -> None:
        """Update an existing show in the database.

        Called when ``Show.update_at > datetime.now()``.

        By default this will clear ``Show.update_at``, override to implement ``Plugin``
        specific update logic.

        Args:
            show: The ``Show`` to update.
        """
        show.update_at = None

    def update_season(self, season: Season) -> None:
        """Update an existing season in the database.

        Called when ``Season.update_at > datetime.now()``.

        By default this will clear ``Season.update_at``, override to implement
        ``Plugin`` specific update logic.

        Args:
            season: The ``Season`` to update.
        """
        season.update_at = None

    def update_episode(self, episode: Episode) -> None:
        """Update an existing episode in the database.

        Called when ``Episode.update_at > datetime.now()``.

        By default this will clear ``Episode.update_at``, override to implement
        ``Plugin`` specific update logic.

        Args:
            episode: The ``Episode`` to update.
        """
        episode.update_at = None

    def update_file(self, file: File) -> None:
        """Update an existing file in the database.

        By default this will clear ``File.update_at``, override to implement
        ``Plugin`` specific update logic.

        Args:
            file: The ``File`` to update.
        """
        file.update_at = None

    # endregion import_url

    # region import_watch_history

    import_watch_history_file_extension: str

    @classmethod
    def import_watch_history_instructions(cls) -> str:
        """Markdown text describing how to export and upload watch history."""
        return "This plugin does not have specific watch history import instructions."

    def import_watch_history(
        self,
        content: str,
        user: User,
        *,
        new_only: bool,
        verified: bool,
    ) -> WatchImportResults:
        """Import watch history from the uploaded file contents.

        Args:
            content: Raw file contents uploaded by the user.
            user: User the watches belong to.
            new_only: Skip episodes the user has already marked watched.
            verified: Mark the imported watches as verified.
        """
        msg = "import_watch_history is not supported by this plugin."
        raise NotImplementedError(msg)

    # endregion import_watch_history

    # region Search

    def search(self, query: str) -> PluginSearchResults:
        """Search for media."""
        msg = "search is not supported by this plugin."
        raise NotImplementedError(msg)

    # endregion Search

    # region Meta Functions

    @override
    def __init_subclass__(cls, *, register: bool = True, **kwargs: Any) -> None:
        """Auto-register every concrete subclass as a plugin.

        Pass ``register=False`` in the subclass declaration to opt out. That's
        used for intermediate mixin classes that shouldn't appear as their own
        plugin in the registry.
        """
        super().__init_subclass__(**kwargs)
        if register:
            register_plugins(cls)

    @classmethod
    def implements(cls, method_name: str) -> bool:
        """Return True when the subclass has overridden ``method_name``.

        Used to determine if a plugins supports ``Plugin.import_url()``,
        ``Plugin.search()``, or ``Plugin.import_watch_history()``.
        """
        child_implementation = inspect.getattr_static(cls, method_name)
        abstract_implementation = inspect.getattr_static(AbstractPlugin, method_name)
        return child_implementation is not abstract_implementation

    # endregion Meta Functions


# region Import URL


class InvalidURLError(Exception):
    """Raised during ``import_url`` when a URL with a correct format is invalid."""


class URLImportResult(BaseModel):
    """Result of importing a single URL.


    Example outputs:

      If a user adds a URL for a show it is assumed the user wants every season/episode
      of that shows and all future episodes as well so the output should be:
          show=show - Show is always required whitelist_mode=False - New
          seasons/episodes should be added automatically.

      If the user adds a URL for a season it is assumed the user wants just the episodes
      from that season and all other seasons/episodes should be excluded so the output
      should be:
          show=show - Show is always required seasons=[season] - Just the imported
          season should be whitelisted. whitelist_mode=True - New seasons need to be
          manually whitelisted.

      If the user adds a URL for an episode it is assumed the user wants just that
      episode and all other seasons/episodes should be excluded so the output should be:
          show=show - Show is always required
          episodes=[episode] - Just the imported episode should be whitelisted.
          whitelist_mode=True - New episodes need to be manually whitelisted.

    Let this be a Sequence because SQLModel defaults to Sequences.

    """

    show: Show
    """The show that was imported from the URL."""

    seasons: list[Season] = Field(default=[])
    """Seasons to prepopulate in the user's whitelist/blacklist."""

    episodes: list[Episode] = Field(default=[])
    """Episodes to prepopulate in the user's whitelist/blacklist."""

    whitelist_mode: bool = Field(default=False)
    """Opt-in (True) vs. opt-out (False) behavior for new content.

    When True, future seasons/episodes the plugin discovers are NOT added to
    the user's channel automatically — the user must whitelist each one.
    When False (the default), new content is added automatically and the user
    must blacklist anything they don't want.
    """


# endregion Import URL

# region Search


class PluginSearchResultSource(BaseModel):
    """Source information for a search result.

    Used for plugins that support multiple sources.
    """

    name: str
    """Name of the source."""
    icon_url: str | None = None
    """URL for an icon representing the source."""


class PluginSearchResult(BaseModel):
    """Search result from a plugin."""

    title: str
    """Title of the search result."""
    url: str
    """URL of the search result."""
    year: int | None = None
    """Release year of the search result."""
    image_url: str | None = None
    """URL of the image representing the search result."""
    media_type: str | None = None
    """Media type of the search result."""
    sources: list[PluginSearchResultSource] = Field(default=[])


class PluginSearchResults(BaseModel):
    """Results from a search query."""

    has_source_selection: bool
    """Whether the user needs to select a source before adding the URL."""
    results: list[PluginSearchResult]


# endregion Search
