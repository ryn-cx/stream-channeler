# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.canonical_media.service import canonical_ids_by_key
from app.channels.service import shows_by_canonical_id
from app.shows.models import Show
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugins.JustWatch import JustWatch

_SEASON_NUMBER_REGEX = r"\/season-(\d+)"


# TODO: Validate
class JustWatchURLHandler(URLHandler["JustWatch"]):
    # TODO: Validate
    def __init__(self, plugin: JustWatch, url: str, show_key: str) -> None:
        self._show_key = show_key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    def show_key(self) -> str:
        """Return the path that identifies the title, e.g. `/us/movie/megamind`."""
        return self._show_key

    # TODO: Validate
    @property
    def season_number(self) -> int | None:
        """Return the season number of the URL, if it is a season URL."""
        match = re.search(_SEASON_NUMBER_REGEX, self.url)
        return int(match.group(1)) if match else None

    # TODO: Validate
    def raise_if_invalid(self) -> None:
        details_file = self.plugin.url_title_details_file(self.show_key)
        self.plugin.raise_if_invalid_file(details_file, self.url)

    # TODO: Validate
    def import_results_for_shows(
        self,
        shows: Sequence[Show],
    ) -> list[URLImportResult]:
        """Return the import results for every show the URL maps to."""
        return [result for show in shows for result in self._results_for_show(show)]

    # TODO: Validate
    def narrow_to_season(
        self,
        results: Sequence[URLImportResult],
    ) -> list[URLImportResult]:
        """Narrow results imported by another plugin down to the URL's season.

        The offer URL handed to the other plugin points at the whole title, so a
        season URL has to be applied to the title it imported. A result names
        that title by the key of the record it wrote, so the copies standing
        behind it are looked up to find which of their seasons the URL asked for.
        """
        if self.season_number is None:
            return list(results)

        canonical_ids = canonical_ids_by_key(
            self.plugin.session,
            {result.show_key for result in results},
            Show,
        )
        copies = shows_by_canonical_id(self.plugin.session, set(canonical_ids.values()))
        return [
            narrowed
            for result in results
            if result.show_key in canonical_ids
            for show in copies[canonical_ids[result.show_key]]
            for narrowed in self._results_for_show(show)
        ]

    # TODO: Validate
    def _results_for_show(self, show: Show) -> list[URLImportResult]:
        # If no season was specified the whole show should be imported.
        season_number = self.season_number
        if season_number is None:
            return [URLImportResult.for_show(show)]

        # If the URL that the user used was for a specific season only return that
        # season. The season.key value in the database is the internal one used by
        # JustWatch, but the user's input will be the external one so the easiest way
        # to match a season is by using the actual season number.
        return [
            URLImportResult.for_seasons(show, [season])
            for season in show.seasons
            if season.season_number == season_number and season.episodes
        ]


# TODO: Validate
class TitleURLHandler(JustWatchURLHandler):
    # https://www.justwatch.com/us/tv-show/kaiju-no-8
    # https://www.justwatch.com/us/tv-show/kaiju-no-8/season-1
    # https://www.justwatch.com/us/movie/weapons-2026
    _URL_REGEX = (
        r"(\/[a-zA-Z]{2}\/(?:tv-show|movie)\/[^\/?#]+)(?:\/season-\d+)?\/?(?:[?#].*)?$"
    )
