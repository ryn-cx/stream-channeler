# TODO: Validate
from typing import Literal, override
from urllib.parse import quote_plus

from app.shows.models import Show
from app.sources.models import Source
from plugins.Amazon.files import FileMixin


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
            return self._tmdb_search_media(page.title(), "movie")
        return self._tmdb_search_media(page.series_title())

    @override
    def _tmdb_media_type(self, show_key: str) -> Literal["movie", "tv"]:
        return "movie" if self._is_movie(show_key) else "tv"

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

    def _channel_source(self, show_key: str, default: Source) -> Source:
        """Return the `Source` for a title, split out per Amazon Channel.

        A title that needs its own subscription (e.g. HBO Max through Prime Video)
        is not part of Prime Video itself, so it gets a `Source` of its own.
        """
        channel = self.detail_page(show_key).channel()
        if channel is None:
            return default

        source_key = f"{self.plugin_key()}:{channel.benefit_id}"
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=f"{self.plugin_name()} ({channel.name})",
            favicon_url=self.FAVICON_URL,
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, existing_source)
