from __future__ import annotations

import json
from functools import cache
from typing import override

from deforestation import Deforestation
from deforestation.detail import Detail as DetailEndpoint
from deforestation.detail.models import ParsedDetailModel
from deforestation.exceptions import TitleNotFoundError

from plugins.utils.base_plugin.files import APIClientFile
from plugins.utils.proxy_client import proxy_client


@cache
def deforestation() -> Deforestation:
    return Deforestation(get_around_client=proxy_client(), region="US")


class Detail(APIClientFile[ParsedDetailModel]):
    @override
    def _endpoint(self) -> DetailEndpoint:
        return deforestation().detail

    @override
    def _download_file(self) -> str:
        return json.dumps(self._endpoint().download_all(self.unique_identifier))

    @override
    def _parse(self, content: str) -> ParsedDetailModel:
        return self._endpoint().load_all(json.loads(content), self.log_id())

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        # Occurs when a user puts in an invalid URL.
        return isinstance(error, TitleNotFoundError)

    def other_title_urls_on_this_page(
        self,
        container_title: str | None = None,
    ) -> set[str]:
        return {
            title.url
            for container in self.parsed().containers
            if container_title is None or container.title == container_title
            for title in container.titles
        }
