from __future__ import annotations

import uuid
from abc import ABC
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select

from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title

if TYPE_CHECKING:
    from sqlalchemy.engine.result import ScalarResult

    from app.plugins.models import Plugin


class BasePreloadMixin(ABC):
    session: Session
    plugin: Plugin

    def _preload_sources(
        self,
        source_key: str | list[str] | None = None,
        *,
        preload_titles: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Source]:
        """Preload the sources with optional related titles, seasons, and episodes.

        If no source_key is provided, all sources for the plugin will be preloaded.
        """
        options: list[Any] = []
        if preload_episodes:
            options.append(
                selectinload(Source.titles)  # type: ignore[arg-type]
                .selectinload(Title.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes),  # type: ignore[arg-type]
            )
        elif preload_seasons:
            options.append(
                selectinload(Source.titles).selectinload(Title.seasons),  # type: ignore[arg-type]  # type: ignore[arg-type]
            )
        elif preload_titles:
            options.append(selectinload(Source.titles))  # type: ignore[arg-type]

        statement = select(Source).where(Source.plugin_id == self.plugin.id)

        if isinstance(source_key, list):
            statement = statement.where(Source.key.in_(source_key))  # type: ignore[attr-defined]
        elif source_key:
            statement = statement.where(Source.key == source_key)
        return self.session.exec(statement.options(*options)).unique()

    def _preload_title(
        self,
        title: str | uuid.UUID,
        source_key: str | None = None,
        *,
        preload_source: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Title]:
        """Preload the title with optional related source, seasons, and episodes."""
        options: list[Any] = []
        if preload_source:
            options.append(joinedload(Title.source))  # type: ignore[arg-type]
        if preload_episodes:
            options.append(
                selectinload(Title.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes)  # type: ignore[arg-type]
                .selectinload(Episode.canonical_episode_links)  # type: ignore[arg-type]
            )
        elif preload_seasons:
            options.append(selectinload(Title.seasons))  # type: ignore[arg-type]
        if isinstance(title, uuid.UUID):
            statement = select(Title).where(Title.id == title)
        else:
            statement = (
                select(Title)
                .join(Source)
                .where(Source.plugin_id == self.plugin.id, Title.key == title)
            )
            if source_key is not None:
                statement = statement.where(Source.key == source_key)
        return self.session.exec(statement.options(*options)).unique()

    def _preload_season(
        self,
        season_id: uuid.UUID,
        *,
        preload_source: bool = False,
        preload_title: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Season]:
        """Preload the season with optional related source, title, and episodes."""
        options: list[Any] = []
        if preload_source:
            options.append(joinedload(Season.title).joinedload(Title.source))  # type: ignore[arg-type]
        elif preload_title:
            options.append(joinedload(Season.title))  # type: ignore[arg-type]
        if preload_episodes:
            options.append(selectinload(Season.episodes))  # type: ignore[arg-type]
        return self.session.exec(
            select(Season).where(Season.id == season_id).options(*options),
        )

    def _preload_episode(
        self,
        episode_id: uuid.UUID,
        *,
        preload_source: bool = False,
        preload_title: bool = False,
        preload_season: bool = False,
    ) -> ScalarResult[Episode]:
        """Preload the episode with optional related source, title, and season."""
        options: list[Any] = []
        if preload_source:
            options.append(
                joinedload(Episode.season)  # type: ignore[arg-type]
                .joinedload(Season.title)  # type: ignore[arg-type]
                .joinedload(Title.source),  # type: ignore[arg-type]
            )
        elif preload_title:
            options.append(
                joinedload(Episode.season).joinedload(Season.title),  # type: ignore[arg-type]
            )
        elif preload_season:
            options.append(joinedload(Episode.season))  # type: ignore[arg-type]
        return self.session.exec(
            select(Episode).where(Episode.id == episode_id).options(*options),
        )
