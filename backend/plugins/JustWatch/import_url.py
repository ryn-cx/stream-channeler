# TODO: Validate
from __future__ import annotations

from typing import override

from app.channels.service import shows_by_identifier
from app.shows.models import Show
from plugins.JustWatch.upsert import UpsertMixin
from plugins.JustWatch.url_handlers import JustWatchURLHandler
from plugins.utils.abstract_plugin import AbstractPlugin, URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class ImportURLMixin(
    UpsertMixin,
    URLHandlerPlugin[JustWatchURLHandler],
    register=False,
):
    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        tmdb_id: int | None = None,
    ) -> list[URLImportResult]:
        """Import the title from every source JustWatch has an offer for.

        JustWatch only knows what an offer links to, so a source that has a plugin
        of its own is imported by that plugin instead. Only the sources without a
        plugin are imported from JustWatch's own data.

        Every source's copy of a title is the same title, so a caller that knows
        which TMDB title this is says so once here and every plugin below works
        from it instead of searching TMDB for the title by its own name.
        """
        self._use_tmdb_id(tmdb_id)
        handler = self.get_url_handler(url)
        handler.raise_if_invalid()

        results: list[URLImportResult] = []
        unhandled_source_keys: list[str] = []
        imported_offer_urls: set[str] = set()
        for source_key, offer in self._sources_with_offers(handler.show_key):
            offer_url = self._clean_external_url(offer.standard_web_url)
            plugin_class = self._plugin_for_url(offer_url)
            if plugin_class is None:
                unhandled_source_keys.append(source_key)
                continue

            # A service that sells more than one plan is listed as a separate
            # package per plan (`nfx` and `nfa` are both Netflix), and every one
            # of them links the same title. The plugin stores one copy of that
            # title, so importing each package would return the same show more
            # than once.
            if offer_url in imported_offer_urls:
                continue
            imported_offer_urls.add(offer_url)

            # The TMDB id is what ties a feed hit back to the copy the other
            # plugin stores, and a title can be delegated on every service it is
            # on, so it is resolved here rather than when a show is upserted.
            title_tmdb_id = self._cached_tmdb_id(handler.show_key)

            plugin_results = plugin_class(self.session).import_url(
                offer_url,
                title_tmdb_id,
            )
            results.extend(
                self._delegated_results(
                    handler,
                    plugin_class,
                    plugin_results,
                    title_tmdb_id,
                ),
            )

        shows = self._import_shows(handler.show_key, unhandled_source_keys)
        results.extend(handler.import_results_for_shows(shows))
        return results

    # TODO: Validate
    def _delegated_results(
        self,
        handler: JustWatchURLHandler,
        plugin_class: type[AbstractPlugin],
        plugin_results: list[URLImportResult],
        tmdb_id: int | None,
    ) -> list[URLImportResult]:
        """Return what another plugin imported, scoped to this plugin's URL.

        A service links its offer at the title, so what the plugin imported is
        already what was asked for. Crunchyroll is the exception and has to be
        asked again.
        """
        if plugin_class.plugin_key() == "Crunchyroll":
            return self._crunchyroll_title_results(
                handler,
                plugin_class,
                plugin_results,
                tmdb_id,
            )
        return handler.narrow_to_season(plugin_results)

    # TODO: Validate
    def _crunchyroll_title_results(
        self,
        handler: JustWatchURLHandler,
        plugin_class: type[AbstractPlugin],
        plugin_results: list[URLImportResult],
        tmdb_id: int | None,
    ) -> list[URLImportResult]:
        """Return the whole title the Crunchyroll offer's episode belongs to.

        Crunchyroll's offer link names a single episode rather than the title,
        so importing it reports only that episode. That import is what resolves
        which show the episode belongs to, and the show it stored knows its own
        URL, so importing that gets the results for the whole title. A result
        names the title by identifier, so the stored copy is looked up to read
        that URL off it. The show is already stored by then, so the second import
        reuses it rather than downloading anything again. It is a fresh instance,
        so it is told the TMDB title again rather than being left to search for
        it by name.
        """
        if len(plugin_results) != 1 or not plugin_results[0].episode_identifiers:
            msg = (
                f"Expected one episode from Crunchyroll, got {len(plugin_results)} "
                f"results: {[result.show_identifier for result in plugin_results]}"
            )
            raise ValueError(msg)

        show_identifier = plugin_results[0].show_identifier
        copies = shows_by_identifier(self.session, {show_identifier})
        show = next(
            (
                copy
                for copy in copies[show_identifier]
                if copy.source.plugin.key == plugin_class.plugin_key() and copy.url
            ),
            None,
        )
        if show is None or show.url is None:
            msg = f"Crunchyroll {show_identifier} has no URL to import the title from"
            raise ValueError(msg)

        return handler.narrow_to_season(
            plugin_class(self.session).import_url(show.url, tmdb_id),
        )

    # TODO: Validate
    def _import_shows(self, show_key: str, source_keys: list[str]) -> list[Show]:
        """Import the title from JustWatch's own data for `source_keys`.

        A title picks up and loses offers over time, so a title that is already
        stored for one source still has to be imported for any source it has since
        become available on.
        """
        if not source_keys:
            return []

        existing_shows = {
            show.source.key: show
            for show in self._preload_show(show_key, preload_source=True).all()
        }
        if all(source_key in existing_shows for source_key in source_keys):
            return [existing_shows[source_key] for source_key in source_keys]

        _cache = (
            self._download_show_files_and_children(show_key),
            # Upserting walks `children` at every level: `add_child` on the
            # source, `soft_delete_missing_children` on the show and season, and
            # `active_children` on the season. Each of those lazy loads its own
            # collection, so the tree is loaded up front for the sources being
            # imported rather than one query per record. The source keys are
            # passed because loading every provider's media would be far worse
            # than the lazy loads this avoids.
            self._preload_sources(source_keys, preload_episodes=True).all(),
        )
        return self._upsert_shows(show_key, source_keys)
