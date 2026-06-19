# TODO: Validate
import re
from abc import ABC, abstractmethod
from typing import Any


class URLMixin(ABC):
    @classmethod
    def is_valid_url_format(cls, url: str) -> bool:
        return re.match(cls._url_regex(), url) is not None

    @classmethod
    @abstractmethod
    def _url_regex(cls) -> str:
        """Return the regex string to check if a URL is supported by the plugin."""

    @classmethod
    @abstractmethod
    def parse_url(cls, url: str) -> Any:  # noqa: ANN401 - TODO: Add a specific return type
        """Parse a URL and return its components.

        Args:
            url: The URL to parse.

        Returns:
            The parsed URL components. The exact type depends on the plugin implementation.
        """

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

    @classmethod
    def _domain(cls) -> str:
        """Return the single (primary) domain the plugin supports.

        Plugins that support exactly one domain should override this. Plugins
        that support multiple domains should override `domains` instead.

        The domain should be in the format of example.com
        """
        return cls.domains()[0]

    @classmethod
    def _base_url(cls) -> str:
        """Return the base URL for the source.

        The base url is in the format of https://www.example.com/
        """
        return f"https://{cls._domain()}/"

    @classmethod
    def build_url(cls, path: str) -> str:
        """Build an absolute URL from a path relative to the base URL.

        A leading slash is added to the path when missing, so callers can pass
        either a bare path (``series/123``) or a root-relative path
        (``/series/123``).
        """
        base_url = cls._base_url().rstrip("/")
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base_url}{path}"

    @classmethod
    def _domain_regex(cls) -> str:
        """Return a regex string that matches all of the source's domains."""
        if len(cls.domains()) > 1:
            escaped_domains = [cls._escape_domain(domain) for domain in cls.domains()]
            return "(?:" + "|".join(escaped_domains) + ")"

        return cls._escape_domain(cls._domain())

    @classmethod
    def _escape_domain(cls, domain: str) -> str:
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
