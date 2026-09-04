# TODO: Validate
from datetime import datetime
from typing import override

from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel

from app.canonical_media.keys import tmdb_season_key
from app.media.media_type import TMDBMediaType
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.files import FileMixin, MovieFileMixin, SeriesFileMixin
from plugins.TMDB.keys import (
    get_media_type_and_tmdb_id,
    parse_episode_key,
    parse_season_key,
)
from plugins.TMDB.utils import EpisodeSource, SeasonSource


# TODO: Validate
class SeasonsMixin(FileMixin):
    """The files and keys the TMDB plugin imports its own media from.

    A season and an episode are keyed by their own TMDB ids, which is what names
    them wherever they are spoken about, while the API is asked for them by the
    numbering they have within the title. The files already downloaded are what
    turn one into the other, so the numbering is read back rather than carried
    around in the key.
    """

    # TODO: Validate
    def _chosen_group(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> TvEpisodeGroupDetailsModel | None:
        group_id = show_chosen_group_id(self.session, self.source, show_key)
        if group_id is None:
            return None
        return self.tv_episode_groups_details_file(group_id).parsed(update_at)

    # TODO: Validate
    @override
    def series_seasons(
        self,
        show_key: str,
        update_at: datetime | None = None,
    ) -> list[SeasonSource]:
        """Return the seasons of a series, in whichever order it is read in.

        A chosen order replaces the title's own outright: its groups are the
        seasons and its episodes are numbered by where the order puts them, not
        by where TMDB's own seasons did. The episodes keep their own ids either
        way, so the same episode is the same row whichever order it is read in
        and a title changing order moves its episodes rather than replacing them.
        """
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        group = self._chosen_group(show_key, update_at)
        if group is not None:
            return [
                SeasonSource(
                    key=tmdb_season_key(TMDBMediaType.tv, order),
                    name=entry.name,
                    season_number=order + 1,
                    poster_path=None,
                    episodes=[
                        EpisodeSource(
                            id=episode.id,
                            number=number,
                            name=episode.name,
                            overview=episode.overview,
                            still_path=episode.still_path,
                            runtime=episode.runtime,
                            air_date=episode.air_date,
                            native_season_number=episode.season_number,
                            native_episode_number=episode.episode_number,
                        )
                        for number, episode in enumerate(entry.episodes, start=1)
                    ],
                )
                for order, entry in enumerate(group.groups)
            ]

        seasons: list[SeasonSource] = []
        details = self.tv_series_details_file(tmdb_id).parsed(update_at)
        for season in details.seasons:
            # A season the title lists but TMDB has no detail for is stored
            # empty, and an empty file has nothing to read a season out of.
            detail = self.tv_seasons_details_file(
                tmdb_id,
                season.season_number,
            ).parsed_or_none(update_at)
            if detail is None:
                continue
            seasons.append(
                SeasonSource(
                    key=tmdb_season_key(TMDBMediaType.tv, season.id),
                    name=detail.name,
                    season_number=season.season_number,
                    poster_path=detail.poster_path,
                    episodes=[
                        EpisodeSource(
                            id=episode.id,
                            number=episode.episode_number,
                            name=episode.name,
                            overview=episode.overview,
                            still_path=episode.still_path,
                            runtime=episode.runtime,
                            air_date=episode.air_date,
                            native_season_number=season.season_number,
                            native_episode_number=episode.episode_number,
                        )
                        for episode in detail.episodes
                    ],
                ),
            )
        return seasons

    # TODO: Validate
    @override
    def _native_season_number(self, season_key: str, show_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, season_tmdb_id = parse_season_key(season_key)
        _, tmdb_id = get_media_type_and_tmdb_id(show_key)
        for season in self.tv_series_details_file(tmdb_id).parsed().seasons:
            if season.id == season_tmdb_id:
                return season.season_number
        message = f"{show_key} has no season {season_key}"
        raise ValueError(message)

    # TODO: Validate
    def season_number(self, season_key: str, show_key: str) -> int:
        """Return the number the title gives the season `season_key` names.

        A title read in a chosen order is numbered by that order, where a
        season's key already carries where in the order it sits, so there is
        nothing to look up.
        """
        if show_chosen_group_id(self.session, self.source, show_key) is not None:
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
                if episode.id == episode_tmdb_id:
                    return episode.number
        message = f"{season_key} has no episode {episode_key}"
        raise ValueError(message)


# TODO: Validate
class SeriesSeasonsMixin(SeriesFileMixin, SeasonsMixin):
    # TODO: Validate
    @override
    def native_season_numbers(self, season_key: str, show_key: str) -> list[int]:
        group_id = show_chosen_group_id(self.session, self.source, show_key)
        if group_id is None:
            return [self._native_season_number(season_key, show_key)]
        _, order = parse_season_key(season_key)
        groups = self.tv_episode_groups_details_file(group_id).parsed().groups
        if order >= len(groups):
            return []
        return sorted({episode.season_number for episode in groups[order].episodes})


# TODO: Validate
class MovieSeasonsMixin(MovieFileMixin, SeasonsMixin):
    # TODO: Validate
    @override
    def native_season_numbers(self, season_key: str, show_key: str) -> list[int]:
        return []
