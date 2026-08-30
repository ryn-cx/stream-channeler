# TODO: Validate
"""Searching a plugin's own imported catalogue."""

from __future__ import annotations

from abc import ABC
from typing import override

from app.episodes.text_matching import TextMatcher
from plugins.utils.base_plugin.plugin import BasePlugin


# TODO: Validate
class CatalogueSearchMixin(BasePlugin, ABC, register=False):
    """What a plugin whose whole catalogue is already imported is searched by.

    A website that holds every title it offers needs no search endpoint of its
    own: the rows already stored are the catalogue, so the closest name among
    them is the answer, and the address is the one the title was imported with.
    """

    MINIMUM_SCORE = 0.5

    # TODO: Validate
    @override
    def search(self, query: str) -> str | None:
        candidates = self._named_shows()
        if not candidates:
            return None

        scores = TextMatcher([name for _url, name in candidates]).blended_scores(query)
        best = max(range(len(scores)), key=lambda index: scores[index])
        if scores[best] < self.MINIMUM_SCORE:
            return None
        return candidates[best][0]

    # TODO: Validate
    def _named_shows(self) -> list[tuple[str, str]]:
        """Return every stored title as the address and name it is known by.

        Keyed by address so a title a website files under more than one source -
        a free listing and a subscription one, say - is offered once.
        """
        named: dict[str, str] = {}
        for source in self._preload_sources(preload_shows=True):
            for show in source.shows:
                if show.deleted_at is None and show.name and show.url:
                    named[show.url] = show.name
        return sorted(named.items())
