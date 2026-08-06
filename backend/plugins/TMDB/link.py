# TODO: Validate
from collections.abc import Sequence
from typing import Literal, Protocol

from tminidb.tv_season_details.models import Episode as TvSeasonEpisode

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from plugins.TMDB.lookup import LookupMixin


class _Named(Protocol):
    name: str


def _plaintext(name: str) -> str:
    return "".join(character for character in name.casefold() if character.isalnum())


def _find_by_name[NamedType: _Named](
    candidates: Sequence[NamedType],
    name: str | None,
) -> NamedType | None:
    if not name:
        return None

    target = _plaintext(name)
    matches = [
        candidate for candidate in candidates if _plaintext(candidate.name) == target
    ]
    return matches[0] if len(matches) == 1 else None


class LinkMixin(LookupMixin, register=False):
    """Points a plugin's own media at the TMDB media standing in for it.

    Only the ids and the `episode_identifier` are stored. Everything a website
    leaves out is read off the linked TMDB record when the media is served, so
    it follows TMDB without the stored record having to be rewritten.
    """

    def tmdb_link_show(
        self,
        show: Show,
        tmdb_id: int | None,
        media_type: Literal["movie", "tv"] = "tv",  # noqa: ARG002 - Kept for a uniform signature.
    ) -> Show:
        """Point a `Show` at its TMDB title."""
        show.tmdb_id = show.tmdb_id or tmdb_id
        return show

    def tmdb_link_season(
        self,
        season: Season,
        tmdb_id: int | None,
        season_number: int | None,
        media_type: Literal["movie", "tv"],
    ) -> Season:
        """Point a `Season` at its TMDB season."""
        if not tmdb_id or season.tmdb_id:
            return season

        if media_type == "movie":
            if movie := self._movie_detail(tmdb_id):
                season.tmdb_id = movie.id
            return season

        seasons = self.show_detail_file(tmdb_id).parsed().seasons
        season_detail = next(
            (
                candidate
                for candidate in seasons
                if candidate.season_number == season_number
            ),
            None,
        )
        if season_detail is None:
            season_detail = _find_by_name(seasons, season.name)
        if season_detail:
            season.tmdb_id = season_detail.id
        return season

    def tmdb_link_episode(
        self,
        episode: Episode,
        tmdb_id: int | None,
        season_number: int | None,
        episode_number: int | None,
        media_type: Literal["movie", "tv"] = "tv",
    ) -> Episode:
        """Point an `Episode` at its TMDB episode.

        The `episode_identifier` is taken from TMDB whenever one is found, since
        it is what makes the same episode on two websites a single episode to
        watch rather than two.
        """
        if not tmdb_id:
            return episode

        if media_type == "movie":
            if movie := self._movie_detail(tmdb_id):
                episode.tmdb_id = episode.tmdb_id or movie.id
                episode.episode_identifier = f"TMDB {movie.id}"
            return episode

        episode_detail = self._episode_detail(
            tmdb_id,
            season_number,
            episode_number,
            episode.name,
        )
        if episode_detail:
            episode.tmdb_id = episode.tmdb_id or episode_detail.id
            episode.episode_identifier = f"TMDB {episode_detail.id}"
        return episode

    def _episode_detail(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
        episode_name: str | None,
    ) -> TvSeasonEpisode | None:
        episodes = self._all_episodes(tmdb_id)

        if episode_detail := _find_by_name(episodes, episode_name):
            return episode_detail

        return self._episode_by_number(tmdb_id, season_number, episode_number)

    def _episode_by_number(
        self,
        tmdb_id: int,
        season_number: int | None,
        episode_number: int | None,
    ) -> TvSeasonEpisode | None:
        if not season_number or not episode_number:
            return None
        if not self.has_season(tmdb_id, season_number):
            return None

        episodes = self.season_detail_file(tmdb_id, season_number).parsed().episodes
        return next(
            (
                candidate
                for candidate in episodes
                if candidate.episode_number == episode_number
            ),
            None,
        )

    _all_episodes_cache: list[TvSeasonEpisode] | None = None

    def _all_episodes(self, tmdb_id: int) -> list[TvSeasonEpisode]:
        """Return every episode of the show the instance is working on.

        Every episode of a show looks its name up in the same list, so without
        caching a show re-reads all of its season files once per episode. The
        list is dropped by `_reset_show_state` when the instance moves to
        another show, so it is held for one show rather than kept per id.
        """
        if self._all_episodes_cache is None:
            episodes: list[TvSeasonEpisode] = []
            for season in self.show_detail_file(tmdb_id).parsed().seasons:
                season_detail = self.season_detail_file(
                    tmdb_id,
                    season.season_number,
                ).parsed()
                episodes.extend(season_detail.episodes)
            self._all_episodes_cache = episodes
        return self._all_episodes_cache
