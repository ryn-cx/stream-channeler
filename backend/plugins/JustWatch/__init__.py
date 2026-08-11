# TODO: Validate
"""JustWatch plugin."""

from __future__ import annotations

from typing import ClassVar

from plugins.JustWatch.helpers import HelperMixin
from plugins.JustWatch.import_url import ImportURLMixin
from plugins.JustWatch.source import SourceMixin
from plugins.JustWatch.upsert import UpsertMixin
from plugins.JustWatch.url_handlers import JustWatchURLHandler, TitleURLHandler


# TODO: Validate
class JustWatch(
    SourceMixin,
    ImportURLMixin,
    UpsertMixin,
    # TODO: Searching is temporarily disabled, add SearchMixin back to re-enable.
    HelperMixin,
    register=True,
):
    """JustWatch plugin."""

    _VERSION = "0.0.1"
    FAVICON_URL = "https://www.justwatch.com/favicon.ico"
    # A title is reached through its TMDB page now, which resolves the JustWatch
    # title behind it. A JustWatch URL still imports if one is pasted.
    LISTED_FOR_IMPORT_URL = False
    _URL_HANDLERS: ClassVar[tuple[type[JustWatchURLHandler], ...]] = (TitleURLHandler,)
