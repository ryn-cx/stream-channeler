# TODO: Validate
"""Reading back where Watchmode says a title can be watched."""

from __future__ import annotations

from datetime import timedelta

from wampi.title_id import tmdb_movie_title_id, tmdb_tv_title_id

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.WatchMode.files import FileMixin

# How long a title's listing stands before it is asked for again. What a service
# carries moves slowly, and every lookup of a TMDB id costs two API credits.
_LISTING_MAX_AGE = timedelta(days=7)


# TODO: Validate
def title_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the Watchmode title id for a TMDB id."""
    if media_type == MediaType.movie:
        return tmdb_movie_title_id(tmdb_id)
    return tmdb_tv_title_id(tmdb_id)


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
        listing_file.download_if_outdated(tz_datetime.now() - _LISTING_MAX_AGE)
        # Empty when Watchmode does not carry the title, which is written as a
        # file with no content rather than raised.
        if not listing_file.database_record.content:
            return []

        urls: list[str] = []
        for item in listing_file.parsed().root:
            if item.web_url and item.web_url not in urls:
                urls.append(item.web_url)
        return urls
