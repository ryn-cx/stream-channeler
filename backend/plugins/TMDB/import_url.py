# TODO: Validate
"""Reading a title in, whether a URL named it or an id did."""

from __future__ import annotations

from typing import Any, override

from bs4 import Tag

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.TMDB.files import title_page_url
from plugins.TMDB.keys import parse_show_key, show_key
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import TMDBURLHandler
from plugins.utils.abstract_plugin import URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin
from plugins.utils.base_plugin.url import URLHandler

# Which half of the catalogue a search of both says a result came from. A multi
# search also returns people, who are no title and cannot be imported.
_SEARCHED_MEDIA_TYPES = {
    "movie": MediaType.movie,
    "tv": MediaType.tv,
}


# TODO: Validate
class ImportURLMixin(
    UpsertMixin,
    LookupMixin,
    URLHandlerPlugin[TMDBURLHandler],
    register=False,
):
    # TODO: Validate
    @override
    def _import_handler(
        self,
        handler: URLHandler[Any],
        canonical_show: Show | None = None,
        *,
        force: bool = False,
    ) -> list[URLImportResult]:
        show_key = handler.show_key
        stored = self._preload_show(show_key).one_or_none()
        if stored is not None and not force:
            return handler.import_results(stored)

        # This title's own rows are written before anything is handed on. A
        # website's plugin resolves the title it carries by asking TMDB for it,
        # so a hand-off made first would be asking for a title that is not
        # stored yet and would send the import straight back round; made after,
        # that ask is answered by the row written here and the chain ends.
        self._download_title_files(show_key)
        show = self.upsert_show(self.source, show_key, force=force)

        # Where the title can be watched is JustWatch's to say, and only when a
        # caller has not already named the title this is of: one that has is a
        # plugin partway through an import of its own, and handing back to it
        # would be that same import a second time.
        if canonical_show is None and (justwatch_url := self._justwatch_url(show_key)):
            # Imported lazily because JustWatch's files use this plugin to
            # resolve TMDB ids, so importing it up here would be circular.
            from plugins.JustWatch import JustWatch  # noqa: PLC0415

            JustWatch(self.session).import_url(justwatch_url, show, force=force)

        return handler.import_results(show)

    # TODO: Validate
    def _download_title_files(self, show_key: str) -> None:
        """Read the title's own file and its seasons', and nothing below them.

        A season carries every episode of it, which is all an upsert here reads,
        so the episode files are left alone. They are two downloads apiece and a
        title runs to hundreds of them; what wants one - matching a website's
        episode to TMDB's - asks for it when it gets there.
        """
        _cache = self._preload_show_files(show_key)
        self._download_outdated_files(self._show_files(show_key))
        for season_key in self._season_keys_from_file(show_key):
            self._download_outdated_files(self._season_files(season_key, show_key))

    # TODO: Validate
    def _justwatch_url(self, show_key: str) -> str | None:
        """Return the JustWatch link TMDB lists among a title's social links."""
        media_type, tmdb_id = parse_show_key(show_key)
        page_file = self.title_page_file(media_type, tmdb_id)
        for link in page_file.parsed().select("a.social_link[href]"):
            if not isinstance(link, Tag):
                continue
            href = str(link["href"])
            if "justwatch.com" in href:
                return href
        return None

    # TODO: Validate
    def import_search(
        self,
        name: str,
        media_type: MediaType | None = None,
        year: int | None = None,
        *,
        force: bool = False,
    ) -> Show | None:
        """Import the first title TMDB returns for `name`.

        `media_type` narrows the search to one half of the catalogue and `year`
        to when the title came out. Neither is required: a search of both halves
        takes whichever half the first result turned out to be from.

        Returns None when TMDB has nothing under that name, since a name is a
        guess at a title in a way an id is not.
        """
        found = self._first_search_result(name, media_type, year)
        if found is None:
            return None

        half, tmdb_id = found
        if half == MediaType.movie:
            return self.import_movie(tmdb_id, force=force)
        return self.import_show(tmdb_id, force=force)

    # TODO: Validate
    def _first_search_result(
        self,
        name: str,
        media_type: MediaType | None,
        year: int | None,
    ) -> tuple[MediaType, int] | None:
        """Return which half the first title TMDB returns is from, and its id."""
        if media_type is not None:
            results = (
                self.auto_updating_search_media(media_type, name, year).parsed().results
            )
            return (media_type, results[0].id) if results else None

        # A search of both halves also returns people, who are no title and are
        # passed over rather than taken as the first result.
        for result in (
            self.auto_updating_search_media(None, name, year).parsed().results
        ):
            half = _SEARCHED_MEDIA_TYPES.get(result.media_type or "")
            if half is not None:
                return half, result.id
        return None

    # TODO: Validate
    def import_show(self, tmdb_id: int, *, force: bool = False) -> Show:
        """Import a TMDB tv entry using a tmdb_id."""
        self.import_url(title_page_url(MediaType.tv, tmdb_id), force=force)
        return self._preload_show(show_key(MediaType.tv, tmdb_id)).one()

    # TODO: Validate
    def import_movie(self, tmdb_id: int, *, force: bool = False) -> Show:
        """Import a TMDB movie entry using a tmdb_id."""
        self.import_url(title_page_url(MediaType.movie, tmdb_id), force=force)
        return self._preload_show(show_key(MediaType.movie, tmdb_id)).one()
