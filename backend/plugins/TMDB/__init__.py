from typing import override

from plugins.TMDB.constants import TMDB_DOMAIN
from plugins.TMDB.files import FileMixin
from plugins.TMDB.media_info import MediaInfoMixin
from plugins.TMDB.search import SearchMixin
from plugins.TMDB.update import UpdateMixin
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.url_handlers import MovieURLHandler, TMDBURLHandler, TvURLHandler
from plugins.TMDB.utils import HelperMixin
from plugins.utils.base_plugin.plugin import URLHandlerPlugin


# TODO: Validate
class TMDB(
    UpdateMixin,
    UpsertMixin,
    SearchMixin,
    MediaInfoMixin,
    HelperMixin,
    FileMixin,
    URLHandlerPlugin[TMDBURLHandler],
    register=True,
):
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    @classmethod
    @override
    def _url_handlers(cls) -> tuple[type[TMDBURLHandler], ...]:
        return (MovieURLHandler, TvURLHandler)

    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN
