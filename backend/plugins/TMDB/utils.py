# TODO: Validate
from datetime import date, datetime
from typing import NamedTuple, override

from tminidb.tv_episode_group.details.models import TvEpisodeGroupDetailsModel

from app.media.media_type import MediaType
from app.utils import tz_datetime
from plugins.TMDB.episode_groups import show_chosen_group_id
from plugins.TMDB.files import FileMixin
from plugins.TMDB.keys import (
    episode_key,
    parse_episode_key,
    parse_season_key,
    parse_show_key,
    season_key,
)


# TODO: Validate
def _image_url(base_url: str, path: str | None) -> str | None:
    return f"{base_url}{path}" if path else None


# TODO: Validate
def release_year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    return int(value[:4]) if value else None


# TODO: Validate
def poster_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w342", path)


# TODO: Validate
def backdrop_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def still_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/original", path)


# TODO: Validate
def logo_image_url(path: str | None) -> str | None:
    return _image_url("https://image.tmdb.org/t/p/w92", path)


# TODO: Validate
def duration_seconds(runtime: int | None) -> int | None:
    return runtime * 60 if runtime else None


# TODO: Validate
def air_datetime(air_date: str | date | None) -> datetime | None:
    # A date TMDB does not have yet comes back as an empty string rather than
    # being left out, and every date the API answers with arrives as the text
    # TMDB wrote rather than as a date.
    if not air_date:
        return None
    if isinstance(air_date, str):
        air_date = date.fromisoformat(air_date)
    return tz_datetime.combine(air_date, datetime.min.time())


# TODO: Validate
def change_datetime(changed_at: str) -> datetime:
    return tz_datetime.fromisoformat(changed_at.replace(" UTC", "+00:00"))


# TODO: Validate
class EpisodeSource(NamedTuple):
    """One episode of a season, and the number the order gives it."""

    id: int
    number: int
    name: str
    overview: str
    still_path: str | None
    runtime: int | None
    air_date: date | None


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
    def _chosen_group(self, show_key: str) -> TvEpisodeGroupDetailsModel | None:
        group_id = show_chosen_group_id(self.session, self.source, show_key)
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
                        EpisodeSource(
                            id=episode.id,
                            number=number,
                            name=episode.name,
                            overview=episode.overview,
                            still_path=episode.still_path,
                            runtime=episode.runtime,
                            air_date=episode.air_date,
                        )
                        for number, episode in enumerate(entry.episodes, start=1)
                    ],
                )
                for order, entry in enumerate(group.groups)
            ]

        seasons: list[SeasonSource] = []
        for season in self.show_detail_file(tmdb_id).parsed().seasons:
            season_file = self.season_detail_file(tmdb_id, season.season_number)
            # Downloaded here rather than left to the caller for the same reason
            # the orders are: what says which seasons a title has is the title's
            # own file, so nothing can name a season file before that has been
            # read, and a title being imported for the first time has none of
            # them stored to be read out of.
            season_file.download_if_outdated()
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
                        EpisodeSource(
                            id=episode.id,
                            number=episode.episode_number,
                            name=episode.name,
                            overview=episode.overview,
                            still_path=episode.still_path,
                            runtime=episode.runtime,
                            air_date=episode.air_date,
                        )
                        for episode in detail.episodes
                    ],
                ),
            )
        return seasons

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
            episode_key(media_type, episode.id)
            for season in self.series_seasons(show_key)
            if season.key in wanted
            for episode in season.episodes
        ]
