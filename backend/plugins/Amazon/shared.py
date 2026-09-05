# TODO: Validate
"""What the plugin, its importers and its initializer all read Prime Video by."""

from __future__ import annotations

from datetime import timedelta
from typing import override

from app.media.media_type import TMDBMediaType
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.Amazon.basic_files import BasicFiles
from plugins.Amazon.constants import (
    MOVIE_ENTITY_TYPE,
    PURCHASE_SOURCE_SUFFIX,
    TITLE_KEY_REGEX,
)
from plugins.Amazon.utils import AmazonSeason, detail_url, search_url

# https://watch.amazon.com/detail?gti=amzn1.dv.gti.92ad2133-d35e-1cb1-5d8e-f7b122a68228
# The id Amazon writes into a share link, which names the title in a
# different id space to the one its own pages are keyed by.
SHARE_URL_REGEX = (
    r"\/detail\?gti=(?P<watch_amazon_title_key>amzn1\.dv\.gti\.[0-9a-f-]+)"
)
# https://www.primevideo.com/detail/0GTKUFQSFLP1YVFDMW9IR56I90
# The region a link was written in is the region of whoever wrote it, and the
# title is the same title whichever region asked for it.
PRIME_VIDEO_URL_REGEX = (
    rf"(?:\/region\/[a-z]{{2}})?\/detail\/(?P<prime_video_title_key>{TITLE_KEY_REGEX})"
)
# https://www.amazon.com/gp/video/detail/B0D9MYVLNM
# The title slug Amazon puts in front of /dp/ is decorative, only the id
# after it matters.
AMAZON_URL_REGEX = (
    r"(?:\/[^\/]+)?\/(?:dp|gp\/video\/detail)\/"
    rf"(?P<amazon_title_key>{TITLE_KEY_REGEX})"
)


# TODO: Validate
class AmazonShared(BasicFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Amazon Prime Video"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return ("Amazon Prime Video", "Amazon Video", "Prime Video")

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.primevideo.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def domains(cls) -> list[str]:
        # Prime Video is read out of its own website, and Amazon's is listed as
        # well because a link to a title on it is a link to the same title.
        # watch.amazon.com is the domain Amazon writes a share link under, and
        # is its own entry because only an optional `www.` is read off a domain.
        return ["primevideo.com", "amazon.com", "watch.amazon.com"]

    # TODO: Validate
    @classmethod
    @override
    def matches_tmdb_provider(cls, provider_name: str) -> bool:
        if super().matches_tmdb_provider(provider_name):
            return True
        return provider_name.endswith("Amazon Channel")

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,  # noqa: ARG002 - `media_type` refines a search.
        year: int | None = None,  # noqa: ARG002 - `year` refines a search.
    ) -> str | None:
        search_file = self.search_file(names[0])
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        results = search_file.results()
        return detail_url(results[0]) if results else None

    # TODO: Validate
    def title_key_from_share_key(self, share_key: str) -> str:
        return self.share_link_file(share_key).title_key()

    # TODO: Validate
    def show_key_from_title_key(self, title_key: str) -> str:
        return self.detail_file(title_key).show_key()

    # TODO: Validate
    def _is_movie(self, title_key: str) -> bool:
        return self.detail_file(title_key).entity_type() == MOVIE_ENTITY_TYPE

    # TODO: Validate
    def _season_available(self, season_key: str) -> bool:
        return self.detail_file(season_key).unavailable_message() is None

    # TODO: Validate
    def _season_entries(self, show_key: str) -> list[AmazonSeason]:
        page = self.detail_file(show_key)
        seasons = page.seasons() or [
            AmazonSeason(
                key=page.compact_key(),
                name=page.title(),
                season_number=page.season_number() or 1,
            ),
        ]
        return [season for season in seasons if self._season_available(season.key)]

    # TODO: Validate
    def title_sources(self, show_key: str) -> list[Source]:
        """Return every `Source` a title belongs to, by how it can be watched.

        A title is often offered more than one way, such as with a channel
        subscription and as a purchase, and each way is a source of its own so
        the title is found however the user can watch it. Only a title included
        with Prime belongs to Prime Video itself.
        """
        detail_file = self.detail_file(show_key)
        sources = [
            self._extra_source(
                f"{self.plugin_name()}:{channel.benefit_id}",
                f"{self.plugin_name()} ({channel.name})",
            )
            for channel in detail_file.channels()
        ]
        if detail_file.included_with_prime():
            sources.append(self.source)
        if detail_file.purchasable():
            sources.append(
                self._extra_source(
                    f"{self.plugin_name()}:{PURCHASE_SOURCE_SUFFIX}",
                    f"{self.plugin_name()} ({PURCHASE_SOURCE_SUFFIX})",
                ),
            )
        # A title with no way to watch it listed still belongs somewhere.
        return sources or [self.source]

    # TODO: Validate
    def _extra_source(self, source_key: str, name: str) -> Source:
        """Return one of the plugin's `Source`s other than its default one."""
        # Looked up against the database rather than only the session, since a
        # source other than the default is made the first time a title needs it
        # and nothing loads it back into a later session before this reads it.
        existing_source = Source.get(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=name,
            favicon_url=self.favicon_url(),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(None)
        return source
