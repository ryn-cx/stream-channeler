# TODO: Validate
"""What every other part of the plugin reads a title by."""

from __future__ import annotations

from datetime import timedelta
from typing import override
from urllib.parse import quote_plus

from app.shows.models import Show
from app.utils import tz_datetime
from plugins.Amazon.files import FileMixin
from plugins.Amazon.keys import title_key_from_location
from plugins.utils.abstract_plugin import InvalidURLError, PluginShowIdentity


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The URLs of a title and the key it is stored under."""

    # TODO: Validate
    @classmethod
    def _detail_url(cls, compact_key: str) -> str:
        return cls.build_url(f"detail/{compact_key}")

    # TODO: Validate
    def _title_url(self, title_key: str) -> str:
        return self._detail_url(self.detail_file(title_key).compact_key())

    # TODO: Validate
    def title_key_from_share_key(self, share_key: str) -> str:
        """Return the id of the title the share link `share_key` names.

        A share link carries an id of Amazon's own that none of Prime Video's
        pages are keyed by, so the id is read off the address the link points
        at rather than out of the link itself.
        """
        redirect_file = self.share_link_file(share_key)
        redirect_file.download_if_outdated()
        location = redirect_file.location() or ""
        landing_key = title_key_from_location(location)
        if landing_key is None:
            msg = f"Amazon share link {share_key} points at no title: {location!r}"
            raise InvalidURLError(msg)
        return landing_key

    # TODO: Validate
    def show_key_from_title_key(self, title_key: str) -> str:
        """Return the key the title `title_key` names is stored under.

        A title can be reached by more than one id, so the key is the id the
        page it opens is addressed by rather than the one the link carried, and
        a title pasted in either way is the one show.

        A series has no page of its own, so every one of its seasons carries the
        whole series and any of them would do as the series. The first is picked
        so that a series pasted in as one season and again as another is the one
        show either way, rather than a show for each way in.
        """
        seasons = self.detail_file(title_key).seasons()
        if not seasons:
            return self.detail_file(title_key).compact_key()
        return min(seasons, key=lambda season: season.season_number).key

    # TODO: Validate
    @override
    @classmethod
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"region/na/search?phrase={quote_plus(query)}")

    # TODO: Validate
    @override
    def show_identity(self, show_key: str) -> PluginShowIdentity:
        detail_file = self.detail_file(show_key)
        detail_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return PluginShowIdentity(
            title=detail_file.series_title(),
            media_type=detail_file.entity_type(),
            year=detail_file.release_year(),
        )


# TODO: Validate
def canonical_show_of(show: Show) -> Show | None:
    """Return the title `show` was found to be linked to, where there is one."""
    if show.canonical_shows:
        return show.canonical_shows[0]
    return None
