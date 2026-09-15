# TODO: Validate

import json
from datetime import datetime
from typing import Any

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.schemas import (
    EpisodeDatabaseColumn,
    EpisodeDatabaseOutput,
    EpisodeDatabaseRow,
)
from app.seasons.models import Season


# TODO: Validate
def _rendered(value: Any) -> str | None:  # noqa: ANN401
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict | list):
        return json.dumps(value, default=str, sort_keys=True)
    return str(value)


# TODO: Validate
def _columns(record: Any, prefix: str = "") -> list[EpisodeDatabaseColumn]:  # noqa: ANN401
    return [
        EpisodeDatabaseColumn(
            name=f"{prefix}{column.name}",
            value=_rendered(getattr(record, column.name)),
        )
        for column in type(record).__table__.columns
    ]


# TODO: Validate
def _season_name(season: Season) -> str | None:
    if season.season_number is not None:
        return f"Season {season.season_number}"
    return season.name


# TODO: Validate
def _label(episode: Episode) -> str:
    season = episode.season
    title = season.title
    parts = [title.source.plugin.key, title.name, _season_name(season)]
    return " · ".join(part for part in parts if part)


# TODO: Validate
def _database_row(
    episode: Episode,
    link: EpisodeTmdbEpisode | None = None,
) -> EpisodeDatabaseRow:
    season = episode.season
    title = season.title
    columns = _columns(episode)
    columns += [
        EpisodeDatabaseColumn(name="season_name", value=_season_name(season)),
        EpisodeDatabaseColumn(name="title_id", value=str(title.id)),
        EpisodeDatabaseColumn(name="title_name", value=title.name),
    ]
    if link is not None:
        columns += _columns(link, "link.")
    return EpisodeDatabaseRow(
        episode_id=episode.id,
        label=_label(episode),
        columns=columns,
    )


# TODO: Validate
def episode_database_rows(episode: Episode) -> EpisodeDatabaseOutput:
    return EpisodeDatabaseOutput(
        episode=_database_row(episode),
        tmdb_episodes=[
            _database_row(link.tmdb_episode, link)
            for link in episode.tmdb_episode_links
        ],
    )
