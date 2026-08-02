# TODO: Validate


import inspect
from abc import ABC, abstractmethod
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import BaseModel, Field

from app.channels.models import ChannelQueue
from app.episodes.models import Episode
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.watches.schemas import WatchImportResults
from plugins.utils.manage_plugins import register_plugins

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.users.models import User


class AbstractPlugin(ABC):
    """Base class every plugin must implement."""

    # The names TMDB uses for this plugin's website in its watch-provider data.
    # A plugin may map to several (e.g. Netflix's base and ad-supported tiers);
    # empty when the plugin has no matching TMDB provider.
    TMDB_PROVIDER_NAMES: ClassVar[tuple[str, ...]] = ()

    # The favicon shown next to this plugin's name in the UI; None when the plugin
    # has no icon of its own.
    FAVICON_URL: ClassVar[str | None] = None

    # When True the plugin is only offered to superusers, so it is left out of the
    # plugin lists returned to regular users.
    SUPERUSER_ONLY: ClassVar[bool] = False

    @classmethod
    @abstractmethod
    def plugin_key(cls) -> str:
        """Return the unique identifier for the plugin.

        Used to match a `Plugin (db)` record with the actual `Plugin (class)`.

        Returns:
            The unique identifier for the plugin.

        """

    @abstractmethod
    def __init__(self, session: Session) -> None:
        """Initialize the plugin class.

        The `Plugin (class)` needs to be able to interact with the database so the
        session should probably be saved to an instance variable like `self.session =
        session`.

        Args:
            session: The database session.

        """

    @classmethod
    def is_valid_url_format(cls, url: str) -> bool:  # noqa: ARG003
        """Check if `url` has the right format for the plugin.

        Does NOT check if `url` is actually valid, this will be done by
        `import_url`.

        Args:
            url: The URL to check.

        Returns:
            True if the URL is valid, False otherwise.

        """
        return False

    def import_url(self, url: str) -> list[URLImportResult]:
        """Import `url` into the database.

        Only called if `is_valid_url_format` returns `True` on the `url`.

        Args:
            url: The URL to import.

        Returns:
            A list of `URLImportResult`.

        Raises:
            `InvalidURLError` if the URL has the correct format but is not actually
            valid.

        """
        msg = "import_url is not supported by this plugin."
        raise NotImplementedError(msg)

    def on_import_url_failure(
        self,
        queue_item: ChannelQueue,  # noqa: ARG002 - `queue_item` is used by overrides.
        error: Exception,
    ) -> None:
        """Handle a failure while importing a URL from a `Channel`'s queue.

        By default the error is re-raised so the caller applies its default
        handling, which marks the URL as failed. Override to reschedule the URL
        instead, by setting `queue_item.status` and `queue_item.import_at`.
        """
        raise error

    @classmethod
    def _read_instructions_file(cls, file_name: str, default: str) -> str:
        """Return the contents of `file_name` from the plugin's directory."""
        instructions_file = Path(inspect.getfile(cls)).parent / file_name
        if not instructions_file.is_file():
            return default
        return instructions_file.read_text(encoding="utf-8")

    # The markdown file, stored next to the plugin, describing the URLs it supports.
    IMPORT_URL_INSTRUCTIONS_FILE: ClassVar[str] = "import_url_instructions.md"

    @classmethod
    @cache
    def import_url_instructions(cls) -> str:
        """Markdown describing what URLs this plugin supports.

        Read once per plugin from `IMPORT_URL_INSTRUCTIONS_FILE`, so the examples can
        be edited without touching the plugin. Add that file to include example URLs
        so users know what to paste.
        """
        return cls._read_instructions_file(
            cls.IMPORT_URL_INSTRUCTIONS_FILE,
            "This plugin does not have specific URL import instructions.",
        )

    def update_plugin(self, plugin: Plugin) -> None:
        """Update an existing plugin in the database.

        Called when `Plugin.update_at > datetime.now()`.

        By default this will clear `Plugin.update_at`, override to implement `Plugin`
        specific update logic.

        Args:
            plugin: The `Plugin` to update.

        """
        plugin.update_at = None

    def update_source(self, source: Source) -> None:
        """Update an existing source in the database.

        Called when `Source.update_at > datetime.now()`.

        By default this will clear `Source.update_at`, override to implement `Plugin`
        specific update logic.

        Args:
            source: The `Source` to update.

        """
        source.update_at = None

    def update_show(self, show: Show, *, force: bool = False) -> None:
        """Update an existing show in the database.

        Called when `Show.update_at > datetime.now()`.

        By default this will clear `Show.update_at`, override to implement `Plugin`
        specific update logic.

        Args:
            show: The `Show` to update.
            force: When True, re-upsert every record even if its data is unchanged.

        """
        show.update_at = None

    def update_season(self, season: Season) -> None:
        """Update an existing season in the database.

        Called when `Season.update_at > datetime.now()`.

        By default this will clear `Season.update_at`, override to implement
        `Plugin` specific update logic.

        Args:
            season: The `Season` to update.

        """
        season.update_at = None

    def update_episode(self, episode: Episode) -> None:
        """Update an existing episode in the database.

        Called when `Episode.update_at > datetime.now()`.

        By default this will clear `Episode.update_at`, override to implement
        `Plugin` specific update logic.

        Args:
            episode: The `Episode` to update.

        """
        episode.update_at = None

    def update_file(self, file: File) -> None:
        """Update an existing file in the database.

        By default this will clear `File.update_at`, override to implement
        `Plugin` specific update logic.

        Args:
            file: The `File` to update.

        """
        file.update_at = None

    # TODO: Consider automatically setting the update_at values to max here.
    def on_update_plugin_failure(self, plugin: Plugin, error: Exception) -> None:  # noqa: ARG002 - `plugin` is used by overrides.
        """Handle a failure while updating a `Plugin`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the plugin instead.
        """
        raise error

    def on_update_source_failure(self, source: Source, error: Exception) -> None:  # noqa: ARG002 - `source` is used by overrides.
        """Handle a failure while updating a `Source`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the source instead.
        """
        raise error

    def on_update_show_failure(self, show: Show, error: Exception) -> None:  # noqa: ARG002 - `show` is used by overrides.
        """Handle a failure while updating a `Show`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the show instead.
        """
        raise error

    def on_update_season_failure(self, season: Season, error: Exception) -> None:  # noqa: ARG002 - `season` is used by overrides.
        """Handle a failure while updating a `Season`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the season instead.
        """
        raise error

    def on_update_episode_failure(self, episode: Episode, error: Exception) -> None:  # noqa: ARG002 - `episode` is used by overrides.
        """Handle a failure while updating an `Episode`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the episode instead.
        """
        raise error

    import_watch_history_file_extension: str

    # The markdown file, stored next to the plugin, describing how to export a watch
    # history. Whether a plugin can import one is decided by `import_watch_history`,
    # not by this file existing.
    IMPORT_WATCH_HISTORY_INSTRUCTIONS_FILE: ClassVar[str] = (
        "import_watch_history_instructions.md"
    )

    @classmethod
    @cache
    def import_watch_history_instructions(cls) -> str:
        """Markdown text describing how to export and upload watch history.

        Read once per plugin from `IMPORT_WATCH_HISTORY_INSTRUCTIONS_FILE`, so the
        steps can be edited without touching the plugin.
        """
        return cls._read_instructions_file(
            cls.IMPORT_WATCH_HISTORY_INSTRUCTIONS_FILE,
            "This plugin does not have specific watch history import instructions.",
        )

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

    def search(self, query: str) -> PluginSearchResults:
        """Search for media."""
        msg = "search is not supported by this plugin."
        raise NotImplementedError(msg)

    @classmethod
    def search_url(cls, query: str) -> str | None:  # noqa: ARG003 - `query` is used by overrides.
        """Return the plugin website's own search-page URL for `query`.

        Lets a user open the source site's search directly to find and copy an
        importable URL. Returns None when the site has no such search page.
        """
        return None

    @override
    def __init_subclass__(cls, *, register: bool = True, **kwargs: Any) -> None:
        """Auto-register every concrete subclass as a plugin.

        Pass `register=False` in the subclass declaration to opt out. That's
        used for intermediate mixin classes that shouldn't appear as their own
        plugin in the registry.
        """
        super().__init_subclass__(**kwargs)
        if register:
            register_plugins(cls)

    @classmethod
    def implements(cls, method_name: str) -> bool:
        """Return True when the subclass has overridden `method_name`.

        Used to determine if a plugins supports `Plugin.import_url()`,
        `Plugin.search()`, or `Plugin.import_watch_history()`.
        """
        child_implementation = inspect.getattr_static(cls, method_name)
        abstract_implementation = inspect.getattr_static(AbstractPlugin, method_name)
        return child_implementation is not abstract_implementation


class InvalidURLError(Exception):
    """Raised during `import_url` when a URL with a correct format is invalid."""


class URLImportResult(BaseModel):
    """Result of importing a single URL.

    Example outputs:

      If a user adds a URL for a show it is assumed the user wants every season/episode
      of that shows and all future episodes as well so the output should be:
          show=show - Show is always required is_whitelist=False - New
          seasons/episodes should be added automatically.

      If the user adds a URL for a season it is assumed the user wants just the episodes
      from that season and all other seasons/episodes should be excluded so the output
      should be:
          show=show - Show is always required seasons=[season] - Just the imported
          season should be whitelisted. is_whitelist=True - New seasons need to be
          manually whitelisted.

      If the user adds a URL for an episode it is assumed the user wants just that
      episode and all other seasons/episodes should be excluded so the output should be:
          show=show - Show is always required
          episodes=[episode] - Just the imported episode should be whitelisted.
          is_whitelist=True - New episodes need to be manually whitelisted.

    Let this be a Sequence because SQLModel defaults to Sequences.

    """

    show: Show
    """The show that was imported from the URL."""

    seasons: list[Season] = Field(default=[])
    """Seasons to prepopulate in the user's whitelist/blacklist."""

    episodes: list[Episode] = Field(default=[])
    """Episodes to prepopulate in the user's whitelist/blacklist."""

    is_whitelist: bool = Field(default=False)
    """Opt-in (True) vs. opt-out (False) behavior for new content.

    When True, future seasons/episodes the plugin discovers are NOT added to
    the user's channel automatically — the user must whitelist each one.
    When False (the default), new content is added automatically and the user
    must blacklist anything they don't want.
    """


class PluginSearchResult(BaseModel):
    """Search result from a plugin.

    Every plugin searches a single source (its own platform), so a result maps
    directly to an importable URL. TMDB is the only multi-source search and has
    its own dedicated endpoints instead of implementing this.
    """

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


class PluginSearchResults(BaseModel):
    """Results from a search query."""

    results: list[PluginSearchResult]
