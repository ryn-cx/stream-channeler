# TODO: Validate
from collections.abc import Sequence
from typing import Any, override

from app.media.media_type import MediaType
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
        return [self.show_detail_file(tmdb_id)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
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
        """Return the number the title gives the season `season_key` names."""
        _, season_tmdb_id = parse_season_key(season_key)
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
        _, tmdb_id = parse_show_key(show_key)
        season_number = self.season_number(season_key, show_key)
        season = self.season_detail_file(tmdb_id, season_number).parsed()
        for episode in season.episodes:
            if episode.id == episode_tmdb_id:
                return episode.episode_number
        message = f"{season_key} has no episode {episode_key}"
        raise ValueError(message)

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [season_key(media_type, tmdb_id)]
        return [
            season_key(media_type, season.id)
            for season in self.show_detail_file(tmdb_id).parsed().seasons
        ]

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

        episode_keys: list[str] = []
        for key in season_keys:
            season_number = self.season_number(key, show_key)
            episode_keys += [
                episode_key(media_type, episode.id)
                for episode in self.season_detail_file(tmdb_id, season_number)
                .parsed()
                .episodes
            ]
        return episode_keys
