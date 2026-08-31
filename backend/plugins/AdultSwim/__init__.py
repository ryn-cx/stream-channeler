# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.shows.models import Show
from plugins.AdultSwim.constants import FREE, SUBSCRIPTION
from plugins.AdultSwim.import_url import ImportURLMixin
from plugins.AdultSwim.update import UpdateMixin
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin_v2.search import CatalogueSearchMixin

if TYPE_CHECKING:
    from collections.abc import Iterable


# TODO: Validate
class AdultSwim(
    UpdateMixin,
    CatalogueSearchMixin,
    ImportURLMixin,
    register=True,
):
    @classmethod
    @override
    def tmdb_provider_names(cls) -> tuple[str, ...]:
        return ("Adult Swim",)

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.adultswim.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "adultswim.com"

    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Adult Swim"

    # TODO: Validate
    @override
    def initialize_sources(self) -> None:
        self._initialize_source(FREE, lambda: self._upsert_source(FREE))
        self._initialize_source(SUBSCRIPTION, lambda: self._upsert_source(SUBSCRIPTION))

    # TODO: Validate
    @override
    def _import_read_url(
        self,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = self._show_key
        shows = self._existing_shows(show_key)

        # If the show already exists and an update is not required just return the
        # import results.
        if shows and not force:
            return self._results_for_shows(shows)

        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
            shows = self._existing_shows(show_key)
            if shows and not force:
                return self._results_for_shows(shows)

        return self._results_for_shows(
            [
                self.upsert_show(source, show_key, canonical_show, force=force)
                for source in self._sources.values()
            ],
        )

    # TODO: Validate
    def _results_for_shows(self, shows: Iterable[Show]) -> list[URLImportResult]:
        return [result for show in shows for result in self._import_results(show)]
