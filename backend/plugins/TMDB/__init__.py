# TODO: Validate
"""TMDB Plugin."""

from typing import override

from plugins.TMDB.files import TMDB_DOMAIN, FileMixin
from plugins.TMDB.helpers import HelperMixin
from plugins.TMDB.import_url import ImportURLMixin
from plugins.TMDB.search import SearchMixin
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import MovieURLHandler, TMDBURLHandler, TvURLHandler
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class TMDB(
    ImportURLMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    FileMixin,
    URLHandlerPlugin[TMDBURLHandler],
    register=True,
):
    """TMDB Plugin."""

    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.themoviedb.org/favicon.ico"
    _URL_HANDLERS = (MovieURLHandler, TvURLHandler)

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN
