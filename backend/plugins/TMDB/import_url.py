# TODO: Validate
"""Reading a title in, whether a URL named it or an id did."""

from __future__ import annotations

from typing import Any, override

from loguru import logger

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.JustWatch import JustWatch
from plugins.TMDB.files import title_page_url
from plugins.TMDB.keys import parse_show_key, show_key
from plugins.TMDB.lookup import LookupMixin
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import TMDBURLHandler
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin.plugin import URLHandlerPlugin
from plugins.utils.base_plugin.url import URLHandler
from plugins.utils.manage_plugins import sorted_plugins
from plugins.WatchMode import WatchMode

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
        if stored and not force:
            return handler.import_results(stored)

        # This title's own rows are written before anything is handed on. A
        # website's plugin resolves the title it carries by asking TMDB for it,
        # so a hand-off made first would be asking for a title that is not
        # stored yet and would send the import straight back round; made after,
        # that ask is answered by the row written here and the chain ends.
        self._download_title_files(show_key)
        show = self.upsert_show(self.source, show_key, force=force)

        if canonical_show is None:
            self._import_listed_sources(show_key, show, force=force)

        return handler.import_results(show)

    # TODO: Validate
    @override
    def update_show(self, show: Show, *, force: bool = False) -> None:
        """Read the title again, and import whatever now lists it.

        An update is the only way a title stored before a lookup was added hears
        about it, since the import that would have asked is long done.

        The listings are never imported forced, however this update was asked
        for: a website's own listing is updated by that website's plugin, and
        writing it out again from here in the middle of a run is what leaves the
        same season being written twice. What is wanted is the listings that are
        not stored yet, and an import of one that is returns straight back.
        """
        super().update_show(show, force=force)
        self._import_listed_sources(show.key, show)

    # TODO: Validate
    def _import_listed_sources(
        self,
        show_key: str,
        show: Show,
        *,
        force: bool = False,
    ) -> None:
        """Import the title from every service Watchmode or JustWatch lists it on.

        Both name each service by a link to the title on it, so the listing a
        website carries is reached by the address of that listing rather than by
        searching the website for the title's name and taking whichever result
        looks closest.

        An address a plugin turns out not to be able to import is passed over
        rather than raised on. Both lookups list a service that sells a disc of
        the title the same way they list one that streams it, and an address
        like that is a shop page rather than a listing anything watches.
        """
        for url in self._listed_source_urls(show_key):
            plugin_class = self._plugin_for_url(url)
            if plugin_class is None:
                continue
            try:
                plugin_class(self.session).import_url(url, show, force=force)
            except InvalidURLError:
                logger.info("Nothing to import at {}", url)

    # TODO: Validate
    def _listed_source_urls(self, show_key: str) -> list[str]:
        """Return every address either lookup gives for the title, without repeats."""
        media_type, tmdb_id = parse_show_key(show_key)
        urls = WatchMode(self.session).source_urls(media_type, tmdb_id)

        # TMDB's page for a title links to JustWatch's page for the same title,
        # so the listing is read straight off that address rather than JustWatch
        # being searched for the title's name.
        page_url = self._justwatch_page_url(media_type, tmdb_id)
        if page_url is not None:
            for url in JustWatch(self.session).source_urls(page_url):
                if url not in urls:
                    urls.append(url)
        return urls

    # TODO: Validate
    def _justwatch_page_url(self, media_type: MediaType, tmdb_id: int) -> str | None:
        """Return the JustWatch address TMDB's page for the title links to.

        The page comes down with an import rather than with an update, so it is
        asked for here: a title stored before this was read is reached by an
        update and has no page of its own yet.
        """
        page_file = self.title_page_file(media_type, tmdb_id)
        page_file.download_if_outdated()
        if not page_file.database_record.content:
            return None

        link = page_file.parsed().select_one('a[href*="justwatch.com"]')
        return None if link is None else str(link["href"])

    # TODO: Validate
    @staticmethod
    def _plugin_for_url(url: str) -> type[AbstractPlugin] | None:
        """Return the plugin that imports `url`, where one accepts it."""
        for plugin_class in sorted_plugins():
            if not plugin_class.implements("import_url"):
                continue
            if plugin_class.is_valid_url_format(url):
                return plugin_class
        return None

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
