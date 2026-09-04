# TODO: Validate
"""Searching a plugin's own imported catalogue."""

from __future__ import annotations

from abc import ABC
from typing import NamedTuple

from app.episodes.text_matching import TextMatcher
from app.media.media_type import TMDBMediaType
from plugins.utils.base_plugin_v3.base import BasePlugin


# TODO: Validate
class NamedShow(NamedTuple):
    """A stored title as the address, name and kind it is known by."""

    url: str
    name: str
    media_type: str | None


# TODO: Validate
class BaseCatalogueSearchMixin(BasePlugin, ABC):
    """What a plugin whose whole catalogue is already imported is searched by.

    A website that holds every title it offers needs no search endpoint of its
    own: the rows already stored are the catalogue, so the closest name among
    them is the answer, and the address is the one the title was imported with.
    """

    MINIMUM_SCORE = 0.5

    # TODO: Validate
    @classmethod
    def tmdb_media_type_to_plugin_media_type(
        cls, media_type: TMDBMediaType
    ) -> tuple[str, ...]:
        """Return what this website files TMDB's `media_type` under.

        A website tells its catalogue apart more finely than TMDB does - TMDB
        holds two halves where a website has films, series, seasons of a series
        sold on their own, music - so one half of TMDB's catalogue answers to
        more than one of a website's own kinds, and a half it carries nothing of
        answers to none.
        """
        if media_type == TMDBMediaType.movie:
            return ("Movie",)
        return ("TV Show", "Series")

    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        wanted = self.tmdb_media_type_to_plugin_media_type(media_type)
        candidates = [show for show in self._named_shows() if show.media_type in wanted]
        if not candidates:
            return None

        matcher = TextMatcher([show.name for show in candidates])
        best_url: str | None = None
        best_score = 0.0
        for name in names:
            for index, score in enumerate(matcher.blended_scores(name)):
                if score > best_score:
                    best_score = score
                    best_url = candidates[index].url
        return best_url if best_score >= self.MINIMUM_SCORE else None

    # TODO: Validate
    def _named_shows(self) -> list[NamedShow]:
        """Return every stored title as the address and name it is known by.

        Keyed by address so a title a website files under more than one source -
        a free listing and a subscription one, say - is offered once.
        """
        named: dict[str, NamedShow] = {}
        for source in self._preload_sources(preload_shows=True):
            for show in source.shows:
                if show.deleted_at is None and show.name and show.url:
                    named[show.url] = NamedShow(show.url, show.name, show.media_type)
        return [named[url] for url in sorted(named)]
