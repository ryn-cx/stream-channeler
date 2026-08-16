# TODO: Validate
from typing import override

from app.media.media_type import MediaType
from plugins.TMDB.files import FileMixin
from plugins.TMDB.keys import (
    episode_key,
    parse_episode_key,
    parse_season_key,
    parse_show_key,
    season_key,
)


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
    def season_number(self, season_key: str, show_key: str) -> int:
        """Return the number the title gives the season `season_key` names.

        A title read in a chosen order is numbered by that order, where a
        season's key already carries where in the order it sits, so there is
        nothing to look up.
        """
        if self._chosen_group_id(show_key) is not None:
            _, season_tmdb_id = parse_season_key(season_key)
            return season_tmdb_id + 1
        return self._native_season_number(season_key, show_key)

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
