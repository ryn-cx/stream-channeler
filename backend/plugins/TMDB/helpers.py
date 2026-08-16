# TODO: Validate
from collections.abc import Sequence
from typing import Any, NamedTuple, override

from tminidb.tv_episode_group_details.models import TvEpisodeGroupDetailsModel

from app.media.media_type import MediaType
from app.shows.models import Show
from plugins.TMDB.episode_groups import chosen_group_id
from plugins.TMDB.files import FileMixin
from plugins.TMDB.keys import (
    episode_key,
    parse_episode_key,
    parse_season_key,
    parse_show_key,
    season_key,
)
from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    number: int
    entry: Any


# TODO: Validate
class SeasonSource(NamedTuple):
    """One season of a title, however the title is being read.

    The two ways of reading a series - TMDB's own seasons and a chosen episode
    order - answer with different files holding different shapes, and everything
    that writes a season wants the same handful of things out of either. So both
    are read into this and nothing downstream asks which it was.
    """

    key: str
    name: str | None
    season_number: int
    poster_path: str | None
    episodes: list[EpisodeSource]


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The files and keys the TMDB plugin imports its own media from.

    A season and an episode are keyed by their own TMDB ids, which is what names
    them wherever they are spoken about, while the API is asked for them by the
    numbering they have within the title. The files already downloaded are what
    turn one into the other, so the numbering is read back rather than carried
    around in the key.
    """

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        # `ShowDetail` downloads every season and episode file along with itself.
        # The episode orders come down with it so one can be chosen without an
        # import of its own, and each order's own episodes are a file apart: a
        # title with six orders is six more downloads to read a list of names,
        # and only the order actually chosen is ever read.
        return [self.show_detail_file(tmdb_id), self.episode_groups_file(tmdb_id)]

    # TODO: Validate
    def _chosen_group_id(self, show_key: str) -> str | None:
        """Return the episode order this title is read in, where one was chosen.

        Read off the stored `Show` rather than off a file, since the choice is a
        `User`'s and nothing TMDB says. A title being imported for the first time
        has no row to have chosen anything yet, which reads as TMDB's own order.
        """
        show = Show.get(self.session, self.source, show_key)
        return chosen_group_id(show.extra) if show else None

    # TODO: Validate
    def _chosen_group(self, show_key: str) -> TvEpisodeGroupDetailsModel | None:
        """Return the chosen episode order itself, where there is one."""
        group_id = self._chosen_group_id(show_key)
        if group_id is None:
            return None
        return self.episode_group_detail_file(group_id).parsed()

    # TODO: Validate
    def series_seasons(self, show_key: str) -> list[SeasonSource]:
        """Return the seasons of a series, in whichever order it is read in.

        A chosen order replaces the title's own outright: its groups are the
        seasons and its episodes are numbered by where the order puts them, not
        by where TMDB's own seasons did. The episodes keep their own ids either
        way, so the same episode is the same row whichever order it is read in
        and a title changing order moves its episodes rather than replacing them.
        """
        _, tmdb_id = parse_show_key(show_key)
        group = self._chosen_group(show_key)
        if group is not None:
            return [
                SeasonSource(
                    key=season_key(MediaType.tv, order),
                    name=entry.name,
                    season_number=order + 1,
                    poster_path=None,
                    episodes=[
                        EpisodeSource(number=number, entry=episode)
                        for number, episode in enumerate(entry.episodes, start=1)
                    ],
                )
                for order, entry in enumerate(group.groups)
            ]

        seasons: list[SeasonSource] = []
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            season_file = self.season_detail_file(tmdb_id, season.season_number)
            # A season the title lists but TMDB has no detail for is stored
            # empty, and an empty file has nothing to read a season out of.
            if not season_file.database_record.content:
                continue
            detail = season_file.parsed()
            seasons.append(
                SeasonSource(
                    key=season_key(MediaType.tv, season.id),
                    name=detail.name,
                    season_number=season.season_number,
                    poster_path=detail.poster_path,
                    episodes=[
                        EpisodeSource(number=episode.episode_number, entry=episode)
                        for episode in detail.episodes
                    ],
                ),
            )
        return seasons

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        group_id = self._chosen_group_id(show_key)
        if group_id is not None:
            return [self.episode_group_detail_file(group_id)]
        return [
            self.season_detail_file(
                tmdb_id,
                self.season_number(season_key, show_key),
            ),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        """Return the file an episode was read out of, which is its season's.

        A season carries every episode of it, so that one file is where an
        episode's own record comes from and what says how current it is. TMDB
        does hold a file per episode, but nothing here is read from it: what
        wants one - matching a website's episode to TMDB's by name - downloads
        it as it gets there, and naming it here would have every import fetch
        two files an episode for nothing.
        """
        return self._season_files(season_key, show_key)

    # TODO: Validate
    def season_number(self, season_key: str, show_key: str) -> int:
        """Return the number the title gives the season `season_key` names.

        A title read in a chosen order is numbered by that order, where a
        season's key already carries where in the order it sits, so there is
        nothing to look up.
        """
        _, season_tmdb_id = parse_season_key(season_key)
        if self._chosen_group_id(show_key) is not None:
            return season_tmdb_id + 1
        _, tmdb_id = parse_show_key(show_key)
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            if season.id == season_tmdb_id:
                return season.season_number
        message = f"{show_key} has no season {season_key}"
        raise ValueError(message)

    # TODO: Validate
    def episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int:
        """Return the number the season gives the episode `episode_key` names."""
        _, episode_tmdb_id = parse_episode_key(episode_key)
        for season in self.series_seasons(show_key):
            if season.key != season_key:
                continue
            for episode in season.episodes:
                if episode.entry.id == episode_tmdb_id:
                    return episode.number
        message = f"{season_key} has no episode {episode_key}"
        raise ValueError(message)

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [season_key(media_type, tmdb_id)]
        return [season.key for season in self.series_seasons(show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]

        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [episode_key(media_type, tmdb_id)]

        wanted = set(season_keys)
        return [
            episode_key(media_type, episode.entry.id)
            for season in self.series_seasons(show_key)
            if season.key in wanted
            for episode in season.episodes
        ]
