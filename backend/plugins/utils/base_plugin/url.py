import re
from abc import abstractmethod
from typing import NamedTuple, override

from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError


class ParsedURL(NamedTuple):
    title_key: str
    season_key: str | None = None
    episode_key: str | None = None


class BaseURLMixin(AbstractPlugin):
    @classmethod
    @abstractmethod
    @override
    def plugin_name(cls) -> str: ...

    @classmethod
    @override
    def is_valid_url_format(cls, url: str) -> bool:
        """Return whether the given URL matches the plugin's URL format."""
        # is not None is used to booleanize the response.
        return re.match(cls._url_regex(), url) is not None

    @classmethod
    @abstractmethod
    def _url_regexes(cls) -> tuple[str, ...]:
        """Return a tuple of URL regex patterns that the plugin supports."""

    @classmethod
    def _url_regex(cls) -> str:
        """Return the regex string to check if a URL is supported by the plugin."""
        domain_regex = cls._domains_regex()
        url_regex = "|".join(
            # Replace all named captures to avoid accidently making illegal regex
            # patterns that contain multiple captures for the same name.
            domain_regex + re.sub(r"\(\?P<[^>]+>", "(?:", url_regex)
            for url_regex in cls._url_regexes()
        )
        return f"(?:{url_regex})"

    @override
    def title_key_from_url(self, url: str) -> str:
        domain_regex = self._domains_regex()
        for url_regex in self._url_regexes():
            match = re.match(domain_regex + url_regex, url)
            if match and (title_key := match.groupdict().get("title_key")):
                return title_key

        msg = f"No title key in {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @classmethod
    def _domains(cls) -> list[str]:
        """Return a list of the domains the plugin supports.

        The first domain is the primary domain which will be used by self._base_url().

        The domains should be in the format of example.com

        Plugins that only support a single domain should override the `_domain` method
        instead.
        """
        # This is used in tests to make sure the regex supports every domain.
        return [cls._domain()]

    @classmethod
    def _domain(cls) -> str:
        """Return the single (primary) domain the plugin supports.

        The domain should be in the format of example.com

        Plugins that support multiple domains should override the `domains` method
        instead.
        """
        return cls._domains()[0]

    @classmethod
    def _base_url(cls) -> str:
        """Return the base URL for the source in the format of https://example.com/."""
        return f"https://{cls._domain()}/"

    @classmethod
    def build_url(cls, path: str) -> str:
        """Build a URL for the URL path.

        Args:
            path (str): The URL path to build the full URL for. Leading slashes will
            automatically be added/removed if necessary.
        """
        return f"{cls._base_url()}{path.lstrip('/')}"

    @classmethod
    def _domains_regex(cls, domains: list[str] | None = None) -> str:
        """Return a regex string that matches all of the source's domains."""
        if domains is None:
            domains = cls._domains()

        if len(domains) > 1:
            escaped_domains = [cls._regex_escape_domain(domain) for domain in domains]
            return "(?:" + "|".join(escaped_domains) + ")"

        return cls._regex_escape_domain(domains[0])

    @classmethod
    def _regex_escape_domain(cls, domain: str) -> str:
        """Escapes a plain text domain.

        The escaping process will make a regex that matches the following:
        - example.com
        - www.example.com
        - http://example.com
        - http://www.example.com
        - https://www.example.com
        - https://example.com

        Args:
            domain (str): The plain text domain to escape. It should be in the format of
            example.com.
        """
        if "." not in domain or domain.startswith(("http://", "https://", "www.")):
            msg = f"Invalid domain format: {domain}"
            raise ValueError(msg)

        return rf"(?:^(?:https?:\/\/)?(?:www\.)?{re.escape(domain)})"
