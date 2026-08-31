from typing import override

from plugins.TMDB.constants import TMDB_DOMAIN
from plugins.TMDB.files import FileMixin
from plugins.TMDB.media_info import MediaInfoMixin
from plugins.TMDB.search import SearchMixin
from plugins.TMDB.update import UpdateMixin
from plugins.TMDB.upsert import UpsertMixin
from plugins.TMDB.utils import HelperMixin


# TODO: Validate
class TMDB(
    UpdateMixin,
    UpsertMixin,
    SearchMixin,
    MediaInfoMixin,
    HelperMixin,
    FileMixin,
    register=True,
):
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.themoviedb.org/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return TMDB_DOMAIN
