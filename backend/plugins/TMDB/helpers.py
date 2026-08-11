# TODO: Validate
from collections.abc import Sequence
from typing import Any, override

from app.media.media_type import MediaType
from plugins.TMDB.files import FileMixin
from plugins.TMDB.keys import (
    MOVIE_EPISODE_NUMBER,
    MOVIE_SEASON_NUMBER,
    episode_key,
    parse_episode_key,
    parse_season_key,
    parse_show_key,
    season_key,
)
from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    """The files and keys the TMDB plugin imports its own media from."""

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
        media_type, tmdb_id, season_number = parse_season_key(season_key)
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        return [self.season_detail_file(tmdb_id, season_number)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        media_type, tmdb_id, season_number, episode_number = parse_episode_key(
            episode_key,
        )
        if media_type == MediaType.movie:
            return [self.movie_detail_file(tmdb_id)]
        return [
            self.episode_detail_file(tmdb_id, season_number, episode_number),
            # Read by `tmdb_link_episode` to match an episode a website named in
            # another language, so it is downloaded alongside the episode rather
            # than one at a time as the matching reaches for them.
            self.episode_translations_file(tmdb_id, season_number, episode_number),
        ]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        media_type, tmdb_id = parse_show_key(show_key)
        if media_type == MediaType.movie:
            return [season_key(media_type, tmdb_id, MOVIE_SEASON_NUMBER)]
        return [
            season_key(media_type, tmdb_id, season.season_number)
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

        episode_keys: list[str] = []
        for key in season_keys:
            media_type, tmdb_id, season_number = parse_season_key(key)
            if media_type == MediaType.movie:
                episode_keys.append(
                    episode_key(
                        media_type,
                        tmdb_id,
                        MOVIE_SEASON_NUMBER,
                        MOVIE_EPISODE_NUMBER,
                    ),
                )
                continue
            episode_keys += [
                episode_key(media_type, tmdb_id, season_number, episode.episode_number)
                for episode in self.season_detail_file(tmdb_id, season_number)
                .parsed()
                .episodes
            ]
        return episode_keys
