# TODO: Validate
from __future__ import annotations

from typing import override

from app.shows.models import Show
from plugins.JustWatch.upsert import UpsertMixin
from plugins.JustWatch.url_handlers import JustWatchURLHandler
from plugins.utils.abstract_plugin import AbstractPlugin, URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


class ImportURLMixin(
    UpsertMixin,
    URLHandlerPlugin[JustWatchURLHandler],
    register=False,
):
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        """Import the title from every source JustWatch has an offer for.

        JustWatch only knows what an offer links to, so a source that has a plugin
        of its own is imported by that plugin instead. Only the sources without a
        plugin are imported from JustWatch's own data.
        """
        handler = self._get_url_handler(url)
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
            self._cached_tmdb_id(handler.show_key)

            plugin_results = plugin_class(self.session).import_url(offer_url)
            results.extend(
                self._delegated_results(handler, plugin_class, plugin_results),
            )

        shows = self._import_shows(handler.show_key, unhandled_source_keys)
        results.extend(handler.import_results_for_shows(shows))
        return results

    def _delegated_results(
        self,
        handler: JustWatchURLHandler,
        plugin_class: type[AbstractPlugin],
        plugin_results: list[URLImportResult],
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
            )
        return handler.narrow_to_season(plugin_results)

    def _crunchyroll_title_results(
        self,
        handler: JustWatchURLHandler,
        plugin_class: type[AbstractPlugin],
        plugin_results: list[URLImportResult],
    ) -> list[URLImportResult]:
        """Return the whole title the Crunchyroll offer's episode belongs to.

        Crunchyroll's offer link names a single episode rather than the title,
        so importing it reports only that episode. That import is what resolves
        which show the episode belongs to, and the show it stored knows its own
        URL, so importing that gets the results for the whole title. The show is
        already stored by then, so the second import reuses it rather than
        downloading anything again.
        """
        if len(plugin_results) != 1 or not plugin_results[0].episodes:
            msg = (
                f"Expected one episode from Crunchyroll, got {len(plugin_results)} "
                f"results: {[result.show.key for result in plugin_results]}"
            )
            raise ValueError(msg)

        show = plugin_results[0].show
        if show.url is None:
            msg = f"Crunchyroll show {show.key} has no URL to import the title from"
            raise ValueError(msg)

        return handler.narrow_to_season(plugin_class(self.session).import_url(show.url))

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
