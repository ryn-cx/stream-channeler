# TODO: Validate
from __future__ import annotations

from typing import override

from app.canonical_media.service import add_canonical_show
from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.NHKWorld.media_info import MediaInfoMixin
from plugins.NHKWorld.search import SearchMixin
from plugins.NHKWorld.source import SourceMixin
from plugins.NHKWorld.upsert import UpsertMixin
from plugins.NHKWorld.url_handlers import NHKWorldURLHandler, ShowURLHandler
from plugins.TMDB import TMDB
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin

# The keys whose TMDB title is being looked up further up the stack. TMDB hands
# a title it has just imported to whichever plugin carries it, taking the
# addresses from Watchmode, so an import can arrive here again partway through its own
# lookup. A key already in flight is left to the caller resolving it.
_TMDB_LOOKUPS_IN_FLIGHT = "nhkworld_tmdb_lookups_in_flight"


# TODO: Validate
class NHKWorld(
    SourceMixin,
    UpsertMixin,
    SearchMixin,
    MediaInfoMixin,
    URLHandlerPlugin[NHKWorldURLHandler],
    register=True,
):
    _VERSION = "0.0.1"

    # TODO: Add support for single episodes
    _URL_HANDLERS = (ShowURLHandler,)
    # TODO: Don't hardcode the favicon URL
    FAVICON_URL = "https://www3.nhk.or.jp/nhkworld/common/site_images/nw_webapp.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "www3.nhk.or.jp"

    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "NHK World"

    # TODO: Validate
    @override  # Asks TMDB which title the programme is before writing anything.
    def _import_handler(
        self,
        handler: NHKWorldURLHandler,
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = handler.show_key
        if not force and (show := self._preload_show(show_key).one_or_none()):
            if canonical_show:
                add_canonical_show(self.session, show, canonical_show)
            return handler.import_results(show)

        # The files come down first because the search is made on the name NHK
        # World's own file gives, and a caller that already named the title is
        # not searched for at all.
        _cache = self._download_show_files_and_children(show_key)
        if canonical_show is None:
            canonical_show = self._tmdb_show(show_key, force=force)
        show = self.upsert_show(self.source, show_key, canonical_show, force=force)
        return handler.import_results(show)

    # TODO: Validate
    def _tmdb_show(self, show_key: str, *, force: bool = False) -> Show | None:
        in_flight: set[str] = self.session.info.setdefault(
            _TMDB_LOOKUPS_IN_FLIGHT,
            set(),
        )
        if show_key in in_flight:
            return None

        in_flight.add(show_key)
        try:
            return TMDB(self.session).import_search(
                self.video_program_file(show_key).parsed()["title"],
                # NHK World carries programmes and nothing else, so every listing
                # is a series as far as TMDB is concerned. It says nothing about
                # when a programme came out, so the name is all TMDB is searched
                # on.
                MediaType.tv,
                force=force,
            )
        finally:
            in_flight.discard(show_key)
