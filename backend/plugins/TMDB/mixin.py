# TODO: Validate
from collections.abc import Iterable, Sequence
from typing import Any, override

from app.canonical_media.keys import SHOW_LEVEL, parse_tmdb_key
from app.canonical_shows.models import CanonicalShow
from app.episodes.models import Episode
from app.media.media_type import MediaType
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils.sentinels import Sentinel
from plugins.TMDB import TMDB
from plugins.TMDB.files import EpisodeDetail, MovieDetails, SeasonDetail, ShowDetail
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile

_UNRESOLVED = Sentinel("TMDB_ID")


# TODO: Validate
def highest_episode_number(numbers: Iterable[int | None]) -> int | None:
    """Return the last episode number a season runs to, ignoring unnumbered ones."""
    return max((number for number in numbers if number is not None), default=None)


# TODO: Validate
class TMDBMixin(BasePlugin, register=False):
    """Wraps TMDB files so they files are downloaded for the TMDB plugin."""

    # TODO: Validate
    @property
    def tmdb(self) -> TMDB:
        """Return the TMDB plugin instance."""
        if not hasattr(self, "_tmdb_plugin"):
            self._tmdb_plugin = TMDB(self.session)
        return self._tmdb_plugin

    # TODO: Validate
    def _tmdb_search_media(
        self,
        title: str,
        media_type: MediaType | None = MediaType.tv,
        year: int | None = None,
    ) -> int | None:
        """Return the best-match TMDB id for a title, or None.

        `media_type` restricts the search to movies or tv series; pass None to
        consider both and take the better title match. `year` narrows movie and
        tv searches to a release/first-air year.
        """
        results = (
            self.tmdb.auto_updating_search_media(media_type, title, year)
            .parsed()
            .results
        )
        return results[0].id if results else None

    # TODO: Validate
    def _fetch_tmdb_id(
        self,
        show_key: str,
        existing_show: Show | None = None,
    ) -> int | None:
        raise NotImplementedError

    # TODO: Validate
    def _merge_and_upsert_show(
        self,
        show: Show,
        source: Source,
        existing_show: Show | None,
        show_key: str,
        tmdb_media_type: MediaType,
    ) -> Show:
        """Store the website's own `Show`, pointed at the TMDB title behind it.

        Nothing is copied off TMDB here. The title is imported as canonical
        media instead, which is what fills in whatever this website leaves out
        when the `Show` is served. A title TMDB does not hold is left for
        `reconcile_show` to give a row of its own.
        """
        tmdb_id = self._cached_tmdb_id(show_key)
        show = self.tmdb.tmdb_link_show(show, tmdb_id, tmdb_media_type)
        if show.tmdb_id:
            self.tmdb.import_title(tmdb_media_type, show.tmdb_id)
        show_files = self._show_files(show_key)
        return show.upsert_and_set_update_at(source, existing_show, show_files)

    # TODO: Validate
    def _merge_and_upsert_season(
        self,
        season: Season,
        show: Show,
        existing_season: Season | None,
        show_key: str,
        tmdb_media_type: MediaType,
    ) -> Season:
        # The title this import is working on rather than the one the listing is
        # chiefly of, so a season brought in under a second title is filed under
        # that title instead of under the first.
        season = self.tmdb.tmdb_link_season(
            season,
            show,
            season.season_number,
            tmdb_media_type,
            self._cached_tmdb_id(show_key),
        )
        season_files = self._season_files(season.key, show_key)
        return season.upsert_and_set_update_at(show, existing_season, season_files)

    # TODO: Validate
    def _merge_and_upsert_episode(  # noqa: PLR0913 - Passed straight to `tmdb_link_episode`.
        self,
        episode: Episode,
        season: Season,
        existing_episode: Episode | None,
        show_key: str,
        tmdb_media_type: MediaType,
        last_episode_number: int | None = None,
    ) -> Episode:
        episode = self.tmdb.tmdb_link_episode(
            episode,
            season,
            episode.episode_number,
            tmdb_media_type,
            last_episode_number,
            self._cached_tmdb_id(show_key),
        )
        episode_files = self._episode_files(episode.key, season.key, show_key)
        return episode.upsert_and_set_update_at(season, existing_episode, episode_files)

    # TODO: Validate
    def _get_season_number(self, season_key: str, show_key: str) -> int | None:
        raise NotImplementedError

    # TODO: Validate
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        raise NotImplementedError

    # TODO: Validate
    def tmdb_media_type(self, show_key: str) -> MediaType:  # noqa: ARG002
        return MediaType.tv

    _tmdb_id: int | None | Sentinel = _UNRESOLVED

    # TODO: Validate
    def _existing_show(self, show_key: str) -> Show | None:
        """Return a stored `Show` for `show_key`, preferring one with a `tmdb_id`.

        A plugin can hold the same `show_key` under more than one `Source`, so
        there can be several copies of the same title. They all resolve to the
        same TMDB entry, which is the only thing the caller reads.
        """
        shows = self._preload_show(show_key).all()
        if not shows:
            return None
        return next((show for show in shows if show.tmdb_id), shows[0])

    # TODO: Validate
    def _cached_tmdb_id(self, show_key: str) -> int | None:
        """Resolve the TMDB id once for the show the instance is working on.

        Every file listing resolves the id, so without caching a show with many
        episodes repeats the same lookup for each of them. The value is dropped
        by `_reset_show_state` when the instance moves to another show, so it is
        held for one show rather than kept per show key.
        """
        if isinstance(self._tmdb_id, Sentinel):
            supplied = self._supplied_tmdb_id_for(show_key)
            self._tmdb_id = (
                supplied
                if supplied is not None
                else self._fetch_tmdb_id(show_key, self._existing_show(show_key))
            )
        return self._tmdb_id

    # TODO: Validate
    def _supplied_tmdb_id_for(self, show_key: str) -> int | None:
        """Return the title a caller named, when it is the one this listing is.

        A caller naming a title from the other half of TMDB's catalogue is
        naming something else the listing is also a copy of - the film a series
        listing carries alongside its seasons - so the listing still has to find
        its own title for itself. Only what the listing is chiefly of is
        answered here; the title itself is linked either way.
        """
        supplied = self._supplied_canonical_show
        if supplied is None:
            return None
        parsed = parse_tmdb_key(supplied.key, SHOW_LEVEL)
        if parsed is None:
            return None
        media_type, tmdb_id = parsed
        if media_type != self.tmdb_media_type(show_key):
            return None
        return tmdb_id

    # TODO: Validate
    def _canonical_show_to_hand_off(self, show_key: str) -> CanonicalShow | None:
        """Return the title to tell another plugin about when handing an import on.

        The title the import started at when there is one, since that is the one
        the whole chain is working from and the one a listing further down may
        turn out to carry alongside its own. Otherwise this listing's own title,
        read in so that there is a row to name rather than only an id.
        """
        if self._supplied_canonical_show is not None:
            return self._supplied_canonical_show
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        return self.tmdb.import_title(self.tmdb_media_type(show_key), tmdb_id)

    # TODO: Validate
    def _tmdb_show_file(self, show_key: str) -> ShowDetail | MovieDetails | None:
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self.tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        return self.tmdb.show_detail_file(tmdb_id)

    # TODO: Validate
    def _tmdb_season_file(
        self,
        season_key: str,
        show_key: str,
    ) -> SeasonDetail | MovieDetails | None:
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self.tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        season_number = self._get_season_number(season_key, show_key)
        if season_number is None:
            return None
        if not self.tmdb.has_season(tmdb_id, season_number):
            return None
        return self.tmdb.season_detail_file(tmdb_id, season_number)

    # TODO: Validate
    def _tmdb_episode_file(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> EpisodeDetail | MovieDetails | None:
        tmdb_id = self._cached_tmdb_id(show_key)
        if tmdb_id is None:
            return None
        if self.tmdb_media_type(show_key) == "movie":
            return self.tmdb.movie_detail_file(tmdb_id)
        season_number = self._get_season_number(season_key, show_key)
        episode_number = self._get_episode_number(episode_key, season_key, show_key)
        if not (season_number and episode_number):
            return None
        if not self.tmdb.has_episode(tmdb_id, season_number, episode_number):
            return None
        return self.tmdb.episode_detail_file(tmdb_id, season_number, episode_number)

    # TODO: Validate
    def _download_files_the_tmdb_lookup_reads(
        self,
        files: Sequence[BaseFile[Any]],
    ) -> None:
        """Download the plugin's own files so the TMDB file can be named.

        Which TMDB file belongs to a record is decided by an id, a media type
        and a season or episode number, all of which the plugin reads out of the
        very files being listed here. They are downloaded through the same
        helper the caller would have used, so nothing is fetched outside the
        normal run and an already current file costs nothing.
        """
        self._download_outdated_files(files)

    # TODO: Validate
    def _append_tmdb_show_file(
        self,
        files: Sequence[BaseFile[Any]],
        show_key: str,
    ) -> list[BaseFile[Any]]:
        self._download_files_the_tmdb_lookup_reads(files)
        tmdb_file = self._tmdb_show_file(show_key)
        return [*files, *([tmdb_file] if tmdb_file else [])]

    # TODO: Validate
    def _append_tmdb_season_file(
        self,
        files: Sequence[BaseFile[Any]],
        season_key: str,
        show_key: str,
    ) -> list[BaseFile[Any]]:
        self._download_files_the_tmdb_lookup_reads(files)
        tmdb_file = self._tmdb_season_file(season_key, show_key)
        return [*files, *([tmdb_file] if tmdb_file else [])]

    # TODO: Validate
    def _append_tmdb_episode_file(
        self,
        files: Sequence[BaseFile[Any]],
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> list[BaseFile[Any]]:
        self._download_files_the_tmdb_lookup_reads(files)
        tmdb_file = self._tmdb_episode_file(episode_key, season_key, show_key)
        return [*files, *([tmdb_file] if tmdb_file else [])]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_show_file([], show_key)

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_season_file([], season_key, show_key)

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._append_tmdb_episode_file([], episode_key, season_key, show_key)
