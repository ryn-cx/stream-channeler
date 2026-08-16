# TODO: Validate
"""Reading back where JustWatch says a title can be watched."""

from __future__ import annotations

from urllib.parse import urlparse

from plugins.JustWatch.files import FileMixin


# TODO: Validate
def page_path(page_url: str) -> str:
    """Return the path JustWatch knows its own page by, without its leading slash."""
    return urlparse(page_url).path.strip("/")


# TODO: Validate
class SourcesMixin(FileMixin, register=False):
    """Looking up the sources a title is available on."""

    # TODO: Validate
    def source_urls(self, page_url: str) -> list[str]:
        """Return the web address of every source carrying the JustWatch title.

        Ordered as JustWatch listed them and with repeats dropped, since a
        service carrying a title more than one way - included with a
        subscription and also for sale - is listed once per way.
        """
        listing_file = self.title_offers_file(page_path(page_url))
        listing_file.download_if_outdated()

        node = listing_file.parsed()["urlV2"]["node"]
        if node is None:
            return []

        urls: list[str] = []
        for offer in node["offers"]:
            url = offer["standardWebURL"]
            if url and url not in urls:
                urls.append(url)
        return urls
