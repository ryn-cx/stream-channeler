import uuid
from abc import ABC
from typing import Any

from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


# arg-type (throughout class) - There is no good way to fix type errors caused by
# joinedload and selectinload.
class PreloadMixin(ABC):
    db: Any
    plugin: Plugin

    def _preload_show(
        self,
        show_key: str | None = None,
        show_id: uuid.UUID | None = None,
        *,
        preload_source: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Show]:
        options: list[Any] = []
        if preload_source:
            options.append(joinedload(Show.source))  # type: ignore[arg-type]
        if preload_episodes:
            options.append(selectinload(Show.seasons).selectinload(Season.episodes))  # type: ignore[arg-type]
        elif preload_seasons:
            options.append(selectinload(Show.seasons))  # type: ignore[arg-type]
        if show_id is not None:
            statement = select(Show).where(Show.id == show_id)
        elif show_key is not None:
            statement = (
                select(Show)
                .join(Source)
                .where(Source.plugin_id == self.plugin.id, Show.key == show_key)
            )
        else:
            msg = "Either show_key or show_id must be provided"
            raise ValueError(msg)
        return self.db.exec(statement.options(*options)).unique()

    def _preload_season(
        self,
        season_id: uuid.UUID,
        *,
        preload_source: bool = False,
        preload_show: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Season]:
        options: list[Any] = []
        if preload_source:
            options.append(joinedload(Season.show).joinedload(Show.source))  # type: ignore[arg-type]
        elif preload_show:
            options.append(joinedload(Season.show))  # type: ignore[arg-type]
        if preload_episodes:
            options.append(selectinload(Season.episodes))  # type: ignore[arg-type]
        return self.db.exec(
            select(Season).where(Season.id == season_id).options(*options),
        )

    def _preload_episode(
        self,
        episode_id: uuid.UUID,
        *,
        preload_source: bool = False,
        preload_show: bool = False,
        preload_season: bool = False,
    ) -> ScalarResult[Episode]:
        options: list[Any] = []
        if preload_source:
            options.append(
                joinedload(Episode.season)  # type: ignore[arg-type]
                .joinedload(Season.show)  # type: ignore[arg-type]
                .joinedload(Show.source),  # type: ignore[arg-type]
            )
        elif preload_show:
            options.append(
                joinedload(Episode.season).joinedload(Season.show),  # type: ignore[arg-type]
            )
        elif preload_season:
            options.append(joinedload(Episode.season))  # type: ignore[arg-type]
        return self.db.exec(
            select(Episode).where(Episode.id == episode_id).options(*options),
        )
