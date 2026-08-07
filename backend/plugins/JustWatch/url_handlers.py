# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.channels.service import shows_by_identifier
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.shows.models import Show
    from plugins.JustWatch import JustWatch

_SEASON_NUMBER_REGEX = r"\/season-(\d+)"


class JustWatchURLHandler(URLHandler["JustWatch"]):
    def __init__(self, plugin: JustWatch, url: str, show_key: str) -> None:
        self._show_key = show_key
        super().__init__(plugin, url)

    @property
    def show_key(self) -> str:
        """Return the path that identifies the title, e.g. `/us/movie/megamind`."""
        return self._show_key

    @property
    def season_number(self) -> int | None:
        """Return the season number of the URL, if it is a season URL."""
        match = re.search(_SEASON_NUMBER_REGEX, self.url)
        return int(match.group(1)) if match else None

    def raise_if_invalid(self) -> None:
        details_file = self.plugin.url_title_details_file(self.show_key)
        self.plugin.raise_if_invalid_file(details_file, self.url)

    def import_results_for_shows(
        self,
        shows: Sequence[Show],
    ) -> list[URLImportResult]:
        """Return the import results for every show the URL maps to."""
        return [result for show in shows for result in self._results_for_show(show)]

    def narrow_to_season(
        self,
        results: Sequence[URLImportResult],
    ) -> list[URLImportResult]:
        """Narrow results imported by another plugin down to the URL's season.

        The offer URL handed to the other plugin points at the whole title, so a
        season URL has to be applied to the title it imported. A result names
        that title by its identifier, so the copies standing behind it are looked
        up to find which of their seasons the URL asked for.
        """
        if self.season_number is None:
            return list(results)

        copies = shows_by_identifier(
            self.plugin.session,
            {result.show_identifier for result in results},
        )
        return [
            narrowed
            for result in results
            for show in copies[result.show_identifier]
            for narrowed in self._results_for_show(show)
        ]

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


class TitleURLHandler(JustWatchURLHandler):
    # https://www.justwatch.com/us/tv-show/kaiju-no-8
    # https://www.justwatch.com/us/tv-show/kaiju-no-8/season-1
    # https://www.justwatch.com/us/movie/weapons-2026
    _URL_REGEX = (
        r"(\/[a-zA-Z]{2}\/(?:tv-show|movie)\/[^\/?#]+)(?:\/season-\d+)?\/?(?:[?#].*)?$"
    )
