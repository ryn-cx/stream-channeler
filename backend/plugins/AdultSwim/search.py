# TODO: Validate
from __future__ import annotations

from typing import override

from app.episodes.text_matching import TextMatcher
from plugins.AdultSwim.files import FileMixin


# TODO: Validate
class SearchMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def search(self, query: str) -> str | None:
        candidates = self._named_shows()
        if not candidates:
            return None

        scores = TextMatcher([name for _key, name in candidates]).blended_scores(query)
        best = max(range(len(scores)), key=lambda index: scores[index])
        if scores[best] < 0.5:  # noqa: PLR2004
            return None
        return self.show_url(candidates[best][0])

    # TODO: Validate
    def _named_shows(self) -> list[tuple[str, str]]:
        named: dict[str, str] = {}
        for source in self._preload_sources(preload_shows=True):
            for show in source.shows:
                if show.deleted_at is None and show.name:
                    named[show.key] = show.name
        return sorted(named.items())
