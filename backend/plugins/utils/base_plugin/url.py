# TODO: Validate
import re
from typing import NamedTuple


# TODO: Validate
class MediaInfo(NamedTuple):
    title_key: str
    season_key: str | None = None
    episode_key: str | None = None


# TODO: Validate
class BaseURLMixin:
    # TODO: Validate
    @classmethod
    def is_valid_url_format(cls, url: str) -> bool:
        return re.match(cls.url_regex(), url) is not None

    # TODO: Validate
    @classmethod
    def url_regex(cls) -> str:
        """Return the regex string to check if a URL is supported by the plugin."""
        raise NotImplementedError

    # TODO: Validate
    def extract_media_info(self, url: str) -> MediaInfo:
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

        The base url is in the format of https://example.com/
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
                cls.regex_escape_domain(domain) for domain in cls.domains()
            ]
            return "(?:" + "|".join(escaped_domains) + ")"

        return cls.regex_escape_domain(cls._domain())

    # TODO: Validate
    @classmethod
    def regex_escape_domain(cls, domain: str) -> str:
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
