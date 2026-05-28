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
    @abstractmethod
    def domains(cls) -> list[str]:
        """Return a list of the domains the plugin supports.

        The first domain should be the primary domain used by self.base_url().

        The domains should be in the format of example.com
        """
        # This is used in tests to make sure the regex supports every domain.

    @classmethod
    def _domain(cls) -> str:
        """Return the first domain the plugin supports."""
        return cls.domains()[0]

    @classmethod
    def _base_url(cls) -> str:
        """Return the base URL for the source.

        The base url is in the format of https://www.example.com/
        """
        return f"https://www.{cls._domain()}/"

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
