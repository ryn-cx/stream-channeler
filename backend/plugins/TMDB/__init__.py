# TODO: Validate
"""TMDB Plugin."""

from typing import ClassVar

from plugins.TMDB.files import FileMixin
from plugins.TMDB.helpers import HelperMixin
from plugins.TMDB.import_url import ImportURLMixin
from plugins.TMDB.link import LinkMixin
from plugins.TMDB.search import SearchMixin
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import (
    MovieURLHandler,
    TMDBURLHandler,
    TvURLHandler,
)


# TODO: Validate
class TMDB(
    ImportURLMixin,
    UpsertMixin,
    LinkMixin,
    SearchMixin,
    HelperMixin,
    FileMixin,
    register=True,
):
    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.themoviedb.org/favicon.ico"
    _URL_HANDLERS: ClassVar[tuple[type[TMDBURLHandler], ...]] = (
        MovieURLHandler,
        TvURLHandler,
    )
