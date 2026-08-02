# TODO: Validate
"""JustWatch plugin."""

from __future__ import annotations

from typing import ClassVar

from plugins.JustWatch.helpers import HelperMixin
from plugins.JustWatch.import_url import ImportURLMixin
from plugins.JustWatch.search import SearchMixin
from plugins.JustWatch.source import SourceMixin
from plugins.JustWatch.upsert import UpsertMixin
from plugins.JustWatch.url_handlers import JustWatchURLHandler, TitleURLHandler


class JustWatch(
    SourceMixin,
    ImportURLMixin,
    UpsertMixin,
    SearchMixin,
    HelperMixin,
    register=True,
):
    """JustWatch plugin."""

    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.justwatch.com/favicon.ico"
    SUPERUSER_ONLY = True
    _URL_HANDLERS: ClassVar[tuple[type[JustWatchURLHandler], ...]] = (TitleURLHandler,)
