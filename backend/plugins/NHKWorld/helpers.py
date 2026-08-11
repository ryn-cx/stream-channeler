# TODO: Validate
from __future__ import annotations

from typing import override

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.NHKWorld.files import FileMixin


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    # TODO: Validate
    @override
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        if existing_show and existing_show.tmdb_id is not None:
            return existing_show.tmdb_id
        program_file = self.video_program_file(show_key)
        program_file.download_if_outdated()
        # NHK World programs carry no release year, so the title is all TMDB gets.
        return self._tmdb_search_media(program_file.parsed().title, MediaType.tv)

    # TODO: Validate
    @override
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        # NHK World has no seasons, so there is no number to match against TMDB.
        return None

    # TODO: Validate
    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        # Episode numbers are this plugin's own running count over a flat,
        # reverse-chronological list, so they do not line up with TMDB's.
        return None
