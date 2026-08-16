# TODO: Validate
"""The file JustWatch's listing of a title is read out of."""

from __future__ import annotations

from typing import Any, cast, override

from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import JSONFile
from plugins.utils.get_around_client import get_around_client

GRAPHQL_URL = "https://apis.justwatch.com/graphql"

COUNTRY = "US"
PLATFORM = "WEB"

TITLE_OFFERS_QUERY = """
query TitleOffers($fullPath: String!, $country: Country!, $platform: Platform!) {
  urlV2(fullPath: $fullPath) {
    node {
      ... on MovieOrShow {
        offers(country: $country, platform: $platform) {
          standardWebURL
        }
      }
    }
  }
}
"""


# TODO: Validate
class TitleOffers(JSONFile[dict[str, Any]]):
    """Every source JustWatch says a title can be watched through."""

    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        page_path: str,
    ) -> None:
        """Initialize the file."""
        self.unique_identifier = page_path
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            response = get_around_client().post(
                GRAPHQL_URL,
                json={
                    "query": TITLE_OFFERS_QUERY,
                    "variables": {
                        "fullPath": f"/{self.unique_identifier}",
                        "country": COUNTRY,
                        "platform": PLATFORM,
                    },
                },
            )
            response.raise_for_status()
            self.write(response.json()["data"])

    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", raw)


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """Reaching the JustWatch file for a title."""

    # TODO: Validate
    def title_offers_file(self, page_path: str) -> TitleOffers:
        """Return the listing file for the JustWatch page at `page_path`."""
        return TitleOffers(self.session, self.plugin, page_path)
