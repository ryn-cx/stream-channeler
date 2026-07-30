# TODO: Validate
from functools import cache
from typing import override

from just_scrape import JustScrape
from just_scrape.exceptions import GraphQLError
from just_scrape.url_title_details.models import UrlTitleDetailsResponse

from plugins.utils.base_plugin.files import GAPIJSON
from plugins.utils.base_plugin.plugin import BasePlugin
from plugins.utils.get_around_client import get_around_client

LOOKUP_ONLY_MESSAGE = (
    "JustWatch is a lookup-only plugin, it imports URLs using other plugins and never "
    "owns any media of its own."
)


@cache
def just_scrape_client() -> JustScrape:
    return JustScrape(get_around_client=get_around_client())


class UrlTitleDetails(GAPIJSON[UrlTitleDetailsResponse]):
    """URL title details file."""

    API_ENDPOINT = just_scrape_client().url_title_details

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, GraphQLError) and "NOT_FOUND" in str(error)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid full_path {self.unique_identifier}"

    @override
    def _get(self) -> UrlTitleDetailsResponse:
        return self.API_ENDPOINT.download_and_parse(f"/{self.unique_identifier}")


class FileMixin(BasePlugin, register=False):
    def url_title_details_file(self, full_path: str) -> UrlTitleDetails:
        """Contains a title's metadata and every offer JustWatch has for it."""
        return self._get_cached_file(
            UrlTitleDetails,
            full_path,
            lambda: UrlTitleDetails(self.session, self.plugin, full_path),
        )
