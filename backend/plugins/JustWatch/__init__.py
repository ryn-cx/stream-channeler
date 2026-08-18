"""JustWatch plugin."""

from __future__ import annotations

from plugins.JustWatch.helpers import HelperMixin
from plugins.JustWatch.import_url import ImportURLMixin
from plugins.JustWatch.source import SourceMixin
from plugins.JustWatch.upsert import UpsertMixin
from plugins.JustWatch.url_handlers import TitleURLHandler


class JustWatch(SourceMixin, ImportURLMixin, UpsertMixin, HelperMixin, register=True):
    """JustWatch plugin."""

    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.justwatch.com/favicon.ico"
    _URL_HANDLERS = (TitleURLHandler,)
