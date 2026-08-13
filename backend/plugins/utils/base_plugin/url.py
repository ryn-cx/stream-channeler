# TODO: Validate
import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.shows.models import Show
from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class URLHandler[PluginT](ABC):
    """Abstract base class for URL handlers."""

    _URL_REGEX: ClassVar[str]
    """The URL regex pattern for the handler."""

    # TODO: Validate
    def __init__(self, plugin: PluginT, url: str) -> None:
        """Initialize the URL handler."""
        self.plugin = plugin
        self.url = url

    # TODO: Validate
    @classmethod
    def _url_regex(cls, domain_regex: str) -> str:
        """Returns the full URL regex for the handler."""
        return domain_regex + cls._URL_REGEX

    # TODO: Validate
    @property
    @abstractmethod
    def show_key(self) -> str:
        """Return the show key extracted from the URL."""

    # TODO: Validate
    @abstractmethod
    def raise_if_invalid(self) -> None:
        """Raises an exception if the URL is invalid."""

    # TODO: Validate
    def import_results(self, show: Show) -> list[URLImportResult]:
        """Return what importing the URL added: the listing and its titles.

        A listing is one website's copy of a title, and what a channel is being
        asked for is the title. Both are returned, since a URL naming a listing
        names the title it is of just as much, and a listing that mixes titles
        is a copy of every one of them. A record that is the title itself has
        none to add and stands alone.
        """
        results = [URLImportResult.for_show(show)]
        results += [
            URLImportResult.for_show(canonical_show)
            for canonical_show in show.canonical_shows
        ]
        return results


# TODO: Validate
class URLMixin(ABC):
    # TODO: Validate
    @classmethod
    def is_valid_url_format(cls, url: str) -> bool:
        return re.match(cls.url_regex(), url) is not None

    # TODO: Validate
    @classmethod
    @abstractmethod
    def url_regex(cls) -> str:
        """Return the regex string to check if a URL is supported by the plugin."""

    # TODO: Replace with get_url_handler style
    # TODO: Validate
    def _parse_url(self, url: str) -> Any:  # noqa: ANN401 - TODO: Add a specific return type
        """Parse a URL and return its components.

        Args:
            url: The URL to parse.

        Returns:
            The parsed URL components. The exact type depends on the plugin implementation.

        """
        raise NotImplementedError

    # TODO: Validate
    @classmethod
    def domains(cls) -> list[str]:
        """Return a list of the domains the plugin supports.

        The first domain should be the primary domain used by self._base_url().

        The domains should be in the format of example.com

        Defaults to the single domain returned by `_domain`; plugins that support
        multiple domains should override this instead.
        """
        # This is used in tests to make sure the regex supports every domain.
        return [cls._domain()]

    # TODO: Validate
    @classmethod
    def _domain(cls) -> str:
        """Return the single (primary) domain the plugin supports.

        Plugins that support exactly one domain should override this. Plugins
        that support multiple domains should override `domains` instead.

        The domain should be in the format of example.com
        """
        return cls.domains()[0]

    # TODO: Validate
    @classmethod
    def _base_url(cls) -> str:
        """Return the base URL for the source.

        The base url is in the format of https://www.example.com/
        """
        return f"https://{cls._domain()}/"

    # TODO: Validate
    @classmethod
    def build_url(cls, path: str) -> str:
        """Build an absolute URL from a path relative to the base URL.

        A leading slash is added to the path when missing, so callers can pass
        either a bare path (`series/123`) or a root-relative path
        (`/series/123`).
        """
        base_url = cls._base_url().rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}"

    # TODO: Validate
    @classmethod
    def _domain_regex(cls) -> str:
        """Return a regex string that matches all of the source's domains."""
        if len(cls.domains()) > 1:
            escaped_domains = [
                cls._regex_escape_domain(domain) for domain in cls.domains()
            ]
            return "(?:" + "|".join(escaped_domains) + ")"

        return cls._regex_escape_domain(cls._domain())

    # TODO: Validate
    @classmethod
    def _regex_escape_domain(cls, domain: str) -> str:
        """Escapes a plain text domain in the format of example.com.

        The escaping process will make a regex that matches the following:
        - example.com
        - www.example.com
        - http://example.com
        - http://www.example.com
        - https://www.example.com
        - https://example.com
        """
        return rf"(?:^(?:https?:\/\/)?(?:www\.)?{re.escape(domain)})"
