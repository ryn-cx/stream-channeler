# TODO: Validate
"""What every other part of the plugin reads an Adult Swim title by."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from plugins.AdultSwim.constants import CLIPS, SUBSCRIPTION

if TYPE_CHECKING:
    from pools_closed.show.models import Episode as EpisodeData
    from pools_closed.show.models import Season as SeasonData
    from pools_closed.show.models import ShowModel


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://adultswim.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"videos/{title_key}")


# TODO: Validate
def episode_url(title_key: str, episode_slug: str) -> str:
    return build_url(f"videos/{title_key}/{episode_slug}")


# TODO: Validate
def source_requires_auth(source_key: str) -> bool:
    return source_key == SUBSCRIPTION


# TODO: Validate
def is_clips_source(source_key: str) -> bool:
    return source_key == CLIPS


# TODO: Validate
def is_clip_season(season: SeasonData) -> bool:
    return season.type == "CLIP"


# TODO: Validate
def season_key(season: SeasonData) -> str:
    if is_clip_season(season):
        return f"clip-{season.number}"
    return str(season.number)


# TODO: Validate
def season_name(season: SeasonData) -> str:
    if is_clip_season(season):
        return f"Clips from Season {season.number}"
    return season.name


# TODO: Validate
def season_keys(title: ShowModel) -> list[str]:
    return [season_key(season) for season in title.seasons]


# TODO: Validate
def episode_keys(title: ShowModel, wanted_season_keys: list[str]) -> list[str]:
    return [
        episode.id
        for season in title.seasons
        if season_key(season) in wanted_season_keys
        for episode in season.episodes
    ]


# TODO: Validate
def source_seasons(title: ShowModel, source_key: str) -> list[SeasonData]:
    return [
        season
        for season in title.seasons
        if is_clip_season(season) == is_clips_source(source_key)
    ]


# TODO: Validate
def source_episodes(season: SeasonData, source_key: str) -> list[EpisodeData]:
    if is_clips_source(source_key):
        return list(season.episodes)
    return [
        episode_data
        for episode_data in season.episodes
        if episode_data.auth == source_requires_auth(source_key)
    ]


# TODO: Validate
def episode_air_date(episode: EpisodeData) -> datetime | None:
    air_date = episode.first_airing or episode.launch_date
    if isinstance(air_date, str):
        return datetime.fromisoformat(air_date)
    return air_date


# TODO: Validate
def episode_key_from_slug(title: ShowModel, episode_slug: str) -> str | None:
    for season in title.seasons:
        for episode in season.episodes:
            if episode.slug == episode_slug:
                return episode.id
    return None
