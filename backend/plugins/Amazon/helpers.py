# TODO: Validate
from typing import override
from urllib.parse import quote_plus

from app.media.media_type import MediaType
from app.shows.models import Show
from app.sources.models import Source
from plugins.Amazon.files import FileMixin

# Names the source that holds the titles that have to be bought or rented.
_PURCHASE_SOURCE_SUFFIX = "Purchase"


class HelperMixin(FileMixin, register=False):
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id:
            return existing_show.tmdb_id
        self.detail_page(show_key).download_if_outdated()
        page = self.detail_page(show_key)
        if self._is_movie(show_key):
            return self._tmdb_search_media(page.title(), MediaType.movie)
        return self._tmdb_search_media(page.series_title())

    @override
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if self._is_movie(show_key) else MediaType.tv

    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        for season in self._season_entries(show_key):
            if season.asin == season_key:
                return season.season_number
        return None

    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        for episode in self.detail_page(season_key).episodes():
            if episode.asin == episode_key:
                return episode.episode_number
        return None

    @classmethod
    def _detail_url(cls, asin: str) -> str:
        return cls.build_url(f"gp/video/detail/{asin}")

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(
            f"s?url=search-alias%3Dinstant-video&field-keywords={quote_plus(query)}",
        )

    def _title_sources(self, show_key: str, default: Source) -> list[Source]:
        """Return every `Source` a title belongs to, by how it can be watched.

        A title is often offered more than one way, such as with a channel
        subscription and as a purchase, and each way is a source of its own so the
        title is found however the user can watch it. Only a title included with
        Prime belongs to Prime Video itself.
        """
        detail_page = self.detail_page(show_key)
        sources = [
            self._extra_source(
                f"{self.plugin_key()}:{channel.benefit_id}",
                f"{self.plugin_name()} ({channel.name})",
            )
            for channel in detail_page.channels()
        ]
        if detail_page.included_with_prime():
            sources.append(default)
        if detail_page.purchasable():
            sources.append(
                self._extra_source(
                    f"{self.plugin_key()}:{_PURCHASE_SOURCE_SUFFIX}",
                    f"{self.plugin_name()} ({_PURCHASE_SOURCE_SUFFIX})",
                ),
            )
        # A title with no way to watch it listed still belongs somewhere.
        return sources or [default]

    def _extra_source(self, source_key: str, name: str) -> Source:
        """Return one of the plugin's `Source`s other than its default one."""
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=name,
            favicon_url=self.FAVICON_URL,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, existing_source)
