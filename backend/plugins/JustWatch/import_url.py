# TODO: Validate
from __future__ import annotations

from typing import override

from app.shows.models import Show
from plugins.JustWatch.upsert import UpsertMixin
from plugins.JustWatch.url_handlers import JustWatchURLHandler
from plugins.utils.abstract_plugin import AbstractPlugin, URLImportResult
from plugins.utils.base_plugin.plugin import URLHandlerPlugin
from plugins.utils.manage_plugins import sorted_plugins


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
        for source_key, offer in self._sources_with_offers(handler.show_key):
            offer_url = self._clean_external_url(offer.standard_web_url)
            plugin_class = self._plugin_for_url(offer_url)
            if plugin_class is None:
                unhandled_source_keys.append(source_key)
                continue

            plugin_results = plugin_class(self.session).import_url(offer_url)
            results.extend(handler.narrow_to_season(plugin_results))

        shows = self._import_shows(handler.show_key, unhandled_source_keys)
        results.extend(handler.import_results_for_shows(shows))
        return results

    def _import_shows(self, show_key: str, source_keys: list[str]) -> list[Show]:
        """Import the title from JustWatch's own data for `source_keys`."""
        if not source_keys:
            return []

        existing_shows = [
            show
            for show in self._preload_show(show_key, preload_source=True).all()
            if show.source.key in source_keys
        ]
        if existing_shows:
            return existing_shows

        _cache = (
            self._download_show_files_and_children(show_key),
            self._preload_sources().all(),
        )
        return self._upsert_shows(show_key, source_keys)

    @classmethod
    def _plugin_for_url(cls, url: str) -> type[AbstractPlugin] | None:
        """Return the plugin that imports `url` itself, if there is one."""
        for plugin_class in sorted_plugins():
            if (
                plugin_class is not cls
                and plugin_class.implements("import_url")
                and plugin_class.is_valid_url_format(url)
            ):
                return plugin_class
        return None
