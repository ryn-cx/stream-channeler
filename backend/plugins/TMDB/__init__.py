# TODO: Validate
from typing import override

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.TMDB.files import (
    LOOKUP_ONLY_MESSAGE,
    FileMixin,
)
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.merge import MergeMixin


class TMDB(
    MergeMixin,
    LookupMixin,
    FileMixin,
    register=True,
):
    _VERSION = "0.0.1"

    # TMDB Just needs to make a plugin database entry to store files.
    @override
    def initialize_source(self) -> None:
        return

    @classmethod
    @override
    def _url_regex(cls) -> str:
        return r"(?!)"

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_source(self, source: Source) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_season(self, season: Season) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)

    @override
    def update_episode(self, episode: Episode) -> None:
        raise NotImplementedError(LOOKUP_ONLY_MESSAGE)
