# TODO: Validate


from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonListOutput,
    SeasonOutput,
    SeasonsPublic,
    SeasonWithEpisodeCountOutput,
)
from app.service.responses import list_response
from app.sources.models import Source
from app.titles.models import Title
from app.users.models import User

SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "title_name": Title.name,
    "source_id": Title.source_id,
    "source_key": Source.key,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.key,
}


# TODO: Validate
def season_list_output(
    session: Session,
    current_user: User,
    read_options: ReadOptions,
) -> SeasonsPublic:
    """Read one page of every `Season`."""
    return list_response(
        session=session,
        base=Season.select_with_plugin_eager(),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )


# TODO: Validate
def title_seasons(
    session: Session,
    title: Title,
) -> list[SeasonWithEpisodeCountOutput]:
    """Return every `Season` stored under `title`, in the order they are read in."""
    counts = dict(
        session.exec(
            select(col(Episode.season_id), func.count())
            .where(col(Episode.season_id).in_([season.id for season in title.seasons]))
            .group_by(col(Episode.season_id)),
        ).all(),
    )
    return [
        SeasonWithEpisodeCountOutput(
            **SeasonOutput.model_validate(season).model_dump(),
            episode_count=counts.get(season.id, 0),
        )
        for season in sorted(
            title.seasons,
            key=lambda season: (
                season.sort_order is None,
                season.sort_order or 0,
                season.season_number is None,
                season.season_number or 0,
                season.key,
            ),
        )
    ]


# TODO: Validate
def season_episodes(season: Season) -> list[EpisodeOutput]:
    """Return every `Episode` stored under `season`, in the order they are read in."""
    return [
        EpisodeOutput.model_validate(episode)
        for episode in sorted(
            season.episodes,
            key=lambda episode: (
                episode.sort_order is None,
                episode.sort_order or 0,
                episode.episode_number is None,
                episode.episode_number or 0,
                episode.key,
            ),
        )
    ]
