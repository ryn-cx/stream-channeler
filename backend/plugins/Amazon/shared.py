# TODO: Validate
"""What the plugin, its importers and its initializer all read Prime Video by."""

from __future__ import annotations

from typing import override

from plugins.Amazon.base_files import AmazonBaseFiles
from plugins.Amazon.constants import TITLE_KEY_REGEX
from plugins.Amazon.utils import search_url

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
class AmazonShared(AmazonBaseFiles):
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
    def title_key_from_share_key(self, share_key: str) -> str:
        return self.share_link_file(share_key).title_key()
