# TODO: Validate
"""Reading back where Watchmode says a title can be watched."""

from __future__ import annotations

from wampi.extract_title_id import extract_title_id

from app.media.media_type import MediaType
from plugins.WatchMode.files import FileMixin


# TODO: Validate
def title_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the Watchmode title id for a TMDB id."""
    if media_type == MediaType.movie:
        return extract_title_id(tmdb_movie_id=tmdb_id)
    return extract_title_id(tmdb_tv_id=tmdb_id)


# TODO: Validate
class SourcesMixin(FileMixin, register=False):
    """Looking up the sources a title is available on."""

    # TODO: Validate
    def source_urls(self, media_type: MediaType, tmdb_id: int) -> list[str]:
        """Return the web address of every source carrying the TMDB title.

        Ordered as Watchmode listed them and with repeats dropped, since a
        service carrying a title more than one way - included with a
        subscription and also for sale - is listed once per way.
        """
        listing_file = self.title_sources_file(title_key(media_type, tmdb_id))
        listing_file.download_if_outdated()
        # Empty when Watchmode does not carry the title, which is written as a
        # file with no content rather than raised.
        if not listing_file.database_record.content:
            return []

        urls: list[str] = []
        for item in listing_file.parsed().sources:
            if item.web_url not in urls:
                urls.append(item.web_url)
        return urls
