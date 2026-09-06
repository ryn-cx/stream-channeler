# TODO: Validate


from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import timedelta
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

from pydantic import BaseModel, Field

from app.channels.models import Channel, ChannelQueue
from app.episodes.models import Episode
from app.files.models import File
from app.media.media_type import TMDBMediaType
from app.plugins.models import Plugin
from app.plugins.schemas import TMDBMediaInfo
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResults
from plugins.utils.manage_plugins import register_plugins

if TYPE_CHECKING:
    from datetime import datetime

    from sqlmodel import Session

    from app.users.models import User


# TODO: Validate
class TMDBLookupInfo(NamedTuple):
    name: str
    media_type: TMDBMediaType | None
    year: int | None


# TODO: Validate
class AbstractPlugin(ABC):
    """Base class every plugin must implement."""

    session: Session
    plugin: Plugin

    # TODO: Validate
    def __init_subclass__(cls, *, register: bool = False, **kwargs: Any) -> None:  # noqa: ANN401 - Handed straight to `super`.
        super().__init_subclass__(**kwargs)
        if register:
            register_plugins(cls)

    # The favicon shown next to this plugin's name in the UI; None when the plugin
    # has no icon of its own.
    # TODO: Validate
    @classmethod
    @abstractmethod
    def favicon_url(cls) -> str | None: ...

    # TODO: Validate
    @classmethod
    def specialized_updater(cls) -> bool:
        return False

    # TODO: Validate
    @classmethod
    @abstractmethod
    def plugin_name(cls) -> str:
        """Return the unique identifier for the plugin.

        Used to match a `Plugin (db)` record with the actual `Plugin (class)`.

        Returns:
            The unique identifier for the plugin.

        """

    # TODO: Validate
    @classmethod
    @abstractmethod
    def matches_tmdb_provider(cls, provider_name: str) -> bool: ...

    # TODO: Validate
    @abstractmethod
    def __init__(
        self,
        session: Session,
        plugin: Plugin | None = None,
        sources: Sequence[Source] | None = None,
    ) -> None:
        """Initialize the plugin class.

        The `Plugin (class)` needs to be able to interact with the database so the
        session should probably be saved to an instance variable like `self.session =
        session`.

        Args:
            session: The database session.

        """

    # TODO: Validate
    @classmethod
    def initialize_db(cls, session: Session) -> None:
        cls(session)

    # TODO: Validate
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

    # TODO: Validate
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

    # TODO: Validate
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

    # TODO: Validate
    @classmethod
    def _read_instructions_file(cls, file_name: str, default: str) -> str:
        """Return the contents of `file_name` from the plugin's directory."""
        instructions_file = Path(inspect.getfile(cls)).parent / file_name
        if not instructions_file.is_file():
            return default
        return instructions_file.read_text(encoding="utf-8")

    # The markdown file, stored next to the plugin, describing the URLs it supports.
    # TODO: Validate
    @classmethod
    def import_url_instructions_file(cls) -> str:
        return "import_url_instructions.md"

    # TODO: Validate
    @classmethod
    @cache
    def import_url_instructions(cls) -> str:
        """Markdown describing what URLs this plugin supports.

        Read once per plugin from `import_url_instructions_file`, so the examples can
        be edited without touching the plugin. Add that file to include example URLs
        so users know what to paste.
        """
        return cls._read_instructions_file(
            cls.import_url_instructions_file(),
            "This plugin does not have specific URL import instructions.",
        )

    # TODO: Validate
    def update_plugin(self, plugin: Plugin) -> None:
        """Update an existing plugin in the database.

        Called when `Plugin.update_at > datetime.now()`.

        By default this will clear `Plugin.update_at`, override to implement `Plugin`
        specific update logic.

        Args:
            plugin: The `Plugin` to update.

        """
        plugin.update_at = None

    # TODO: Validate
    def update_source(self, source: Source, update_at: datetime) -> None:  # noqa: ARG002
        """Update an existing source in the database.

        Called when `Source.update_at > datetime.now()`.

        By default this will clear `Source.update_at`, override to implement `Plugin`
        specific update logic.

        Args:
            source: The `Source` to update.

        """
        source.update_at = None

    # TODO: Validate
    def update_title(self, title: Title, *, force: bool = False) -> None:  # noqa: ARG002 - `force` is used by overrides.
        """Update an existing title in the database.

        Called when `Title.update_at > datetime.now()`.

        By default this will clear `Title.update_at`, override to implement `Plugin`
        specific update logic.

        Args:
            title: The `Title` to update.
            force: When True, re-upsert every record even if its data is unchanged.

        """
        title.update_at = None

    # TODO: Validate
    def update_channel(self, channel: Channel) -> None:
        channel.update_at = tz_datetime.now() + timedelta(days=1)

    # TODO: Validate
    def update_season(self, season: Season) -> None:
        """Update an existing season in the database.

        Called when `Season.update_at > datetime.now()`.

        By default this will clear `Season.update_at`, override to implement
        `Plugin` specific update logic.

        Args:
            season: The `Season` to update.

        """
        season.update_at = None

    # TODO: Validate
    def update_episode(self, episode: Episode) -> None:
        """Update an existing episode in the database.

        Called when `Episode.update_at > datetime.now()`.

        By default this will clear `Episode.update_at`, override to implement
        `Plugin` specific update logic.

        Args:
            episode: The `Episode` to update.

        """
        episode.update_at = None

    # TODO: Validate
    def update_file(self, file: File) -> None:
        """Update an existing file in the database.

        By default this will clear `File.update_at`, override to implement
        `Plugin` specific update logic.

        Args:
            file: The `File` to update.

        """
        file.update_at = None

    # TODO: Consider automatically setting the update_at values to max here.
    # TODO: Validate
    def on_update_plugin_failure(self, plugin: Plugin, error: Exception) -> None:  # noqa: ARG002 - `plugin` is used by overrides.
        """Handle a failure while updating a `Plugin`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the plugin instead.
        """
        raise error

    # TODO: Validate
    def on_update_source_failure(self, source: Source, error: Exception) -> None:  # noqa: ARG002 - `source` is used by overrides.
        """Handle a failure while updating a `Source`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the source instead.
        """
        raise error

    # TODO: Validate
    def on_update_title_failure(self, title: Title, error: Exception) -> None:  # noqa: ARG002 - `title` is used by overrides.
        """Handle a failure while updating a `Title`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the title instead.
        """
        raise error

    # TODO: Validate
    def on_update_season_failure(self, season: Season, error: Exception) -> None:  # noqa: ARG002 - `season` is used by overrides.
        """Handle a failure while updating a `Season`.

        By default the error is re-raised so the caller applies its default
        handling. Override to reschedule the season instead.
        """
        raise error

    # TODO: Validate
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
    # TODO: Validate
    @classmethod
    def import_watch_history_instructions_file(cls) -> str:
        return "import_watch_history_instructions.md"

    # TODO: Validate
    @classmethod
    @cache
    def import_watch_history_instructions(cls) -> str:
        """Markdown text describing how to export and upload watch history.

        Read once per plugin from `import_watch_history_instructions_file`, so the
        steps can be edited without touching the plugin.
        """
        return cls._read_instructions_file(
            cls.import_watch_history_instructions_file(),
            "This plugin does not have specific watch history import instructions.",
        )

    # TODO: Validate
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

    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        """Return the address of the one title `names` name here, or None.

        What TMDB cross references a title against, so the closest match is all
        that matters and its address is all that is read off it. A service a
        user searches for themselves offers `in_app_search` instead.

        A title is written differently on every service that carries it, so
        every name TMDB knows it by is handed over rather than one of them: a
        service holding the title under a name TMDB does not lead with is still
        matched. `media_type` and `year` are what tell two titles of one name
        apart, which a name on its own cannot.

        Args:
            names: Every name TMDB knows the title by, the one it leads with
                first.
            media_type: Which of the two halves of TMDB's catalogue the title
                belongs to.
            year: The year TMDB gives the title, where it gives one.

        """
        msg = "search_for_url is not supported by this plugin."
        raise NotImplementedError(msg)

    # TODO: Validate
    def import_search(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> list[URLImportResult]:
        """Import the title `names` name here.

        What TMDB hands a service it has listed a title on, since a service is
        reached by the name of the title rather than by an address when TMDB has
        no address for it. `media_type` and `year` are TMDB's own account of the
        title and are there to tell two titles of one name apart, which a name
        on its own cannot.

        Args:
            names: Every name TMDB knows the title by, the one it leads with
                first.
            media_type: Which of a film and a series the title is.
            year: The year TMDB gives the title, where it gives one.

        Returns:
            A list of `URLImportResult`.

        Raises:
            `MediaNotFoundError` if the service carries no title of that name.

        """
        msg = "import_search is not supported by this plugin."
        raise NotImplementedError(msg)

    # TODO: Validate
    def in_app_search(
        self,
        query: str,
        cursor: str | None = None,
    ) -> PluginSearchResults:
        """Return a page of everything `query` matches, for a user to pick from.

        Paged, since a user reads the results and chooses among them rather than
        taking whatever came first.
        """
        msg = "in_app_search is not supported by this plugin."
        raise NotImplementedError(msg)

    # TODO: Validate
    def media_info(self, media_identifier: str) -> TMDBMediaInfo | None:
        """Return the catalogue detail shown for one of the plugin's own results.

        Args:
            media_identifier: The `media_identifier` of a `PluginSearchResult`
                this same plugin produced.

        """
        msg = "media_info is not supported by this plugin."
        raise NotImplementedError(msg)

    # TODO: Validate
    def tmdb_lookup_info(
        self,
        title_key: str,  # noqa: ARG002 - `title_key` is used by overrides.
    ) -> list[TMDBLookupInfo]:
        return []

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:  # noqa: ARG003 - `query` is used by overrides.
        """Return the plugin website's own search-page URL for `query`.

        Lets a user open the source site's search directly to find and non-canonical row
        an importable URL. Returns None when the site has no such search page.
        """
        return None

    # TODO: Validate
    @classmethod
    def implements(cls, method_name: str) -> bool:
        """Return True when the subclass has overridden `method_name`."""
        child_implementation = inspect.getattr_static(cls, method_name)
        abstract_implementation = inspect.getattr_static(AbstractPlugin, method_name)
        return child_implementation is not abstract_implementation


# TODO: Validate
class InvalidURLError(Exception):
    """Raised during `import_url` when a URL with a correct format is invalid."""


# TODO: Validate
class MediaNotFoundError(Exception):
    pass


# TODO: Validate
class URLImportResult(BaseModel):
    """What a channel takes on from importing a single URL.

    A channel holds the media itself rather than one website's records, so a
    result names what was imported by the keys of the records the plugin just
    wrote, and `add_results_to_channel` resolves each one to the canonical row
    that record is linked to.

    Example outputs:

      If a user adds a URL for a title it is assumed the user wants every
      season/episode of that title and all future episodes as well:
          title_key - Always required.
          is_whitelist=False - New seasons/episodes are added automatically.

      If the user adds a URL for a season it is assumed the user wants just the
      episodes from that season and all other seasons excluded:
          season_keys - Just the imported season.
          is_whitelist=True - New seasons need to be whitelisted by hand.

      If the user adds a URL for an episode it is assumed the user wants just
      that episode and all other episodes excluded:
          episode_keys - Just the imported episode.
          is_whitelist=True - New episodes need to be whitelisted by hand.

    """

    title: Title
    """The title that was imported from the URL."""

    season_keys: list[str] = Field(default=[])
    """Seasons to prepopulate in the user's whitelist/blacklist."""

    episode_keys: list[str] = Field(default=[])
    """Episodes to prepopulate in the user's whitelist/blacklist."""

    is_whitelist: bool = Field(default=False)
    """Opt-in (True) vs. opt-out (False) behavior for new content.

    When True, future seasons/episodes the plugin discovers are NOT added to
    the user's channel automatically — the user must whitelist each one.
    When False (the default), new content is added automatically and the user
    must blacklist anything they don't want.
    """

    # TODO: Validate
    @classmethod
    def title_import_results(
        cls,
        title: Title,
        *,
        is_whitelist: bool = False,
    ) -> URLImportResult:
        """Return the result of importing the whole of `title`."""
        return cls(
            title=title,
            is_whitelist=is_whitelist,
        )

    # TODO: Validate
    @classmethod
    def season_import_results(
        cls,
        title: Title,
        seasons: Sequence[Season],
    ) -> URLImportResult:
        """Return the result of importing only `seasons` of `title`."""
        return cls(
            title=title,
            season_keys=[season.key for season in seasons],
            is_whitelist=True,
        )

    # TODO: Validate
    @classmethod
    def episode_import_results(
        cls,
        title: Title,
        episodes: Sequence[Episode],
    ) -> URLImportResult:
        """Return the result of importing only `episodes` of `title`."""
        return cls(
            title=title,
            episode_keys=[episode.key for episode in episodes],
            is_whitelist=True,
        )


# TODO: Validate
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
    media_identifier: str | None = None
    """What the plugin that produced the result knows the title by.

    Passed back to that same plugin's `media_info` to open the result. Its
    format is the plugin's own — TMDB writes `tv 1399` and `movie 27205`. None
    when the plugin has no details to offer beyond the result itself.
    """


# TODO: Validate
class PluginSearchResults(BaseModel):
    """A single page of results from a search query."""

    results: list[PluginSearchResult]

    next_cursor: str | None = None
    """Cursor to pass back to `search` for the next page.

    None on the last page. Only ever interpreted by the plugin that produced it.
    """
