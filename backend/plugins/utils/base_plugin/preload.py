# TODO: Validate
import uuid
from abc import ABC
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.engine.result import ScalarResult
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.files.models import File
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.utils.base_plugin.files import BaseFile


class PreloadMixin(ABC):
    session: Session
    plugin: Plugin

    def _preload_sources(
        self,
        source_key: str | list[str] | None = None,
        *,
        preload_shows: bool = False,
        preload_seasons: bool = False,
        preload_episodes: bool = False,
    ) -> ScalarResult[Source]:
        options: list[Any] = []
        if preload_episodes:
            options.append(
                selectinload(Source.shows)  # type: ignore[arg-type]
                .selectinload(Show.seasons)  # type: ignore[arg-type]
                .selectinload(Season.episodes),  # type: ignore[arg-type]
            )
        elif preload_seasons:
            options.append(
                selectinload(Source.shows).selectinload(Show.seasons),  # type: ignore[arg-type]  # type: ignore[arg-type]
            )
        elif preload_shows:
            options.append(selectinload(Source.shows))  # type: ignore[arg-type]
        statement = select(Source).where(Source.plugin_id == self.plugin.id)
        if isinstance(source_key, list):
            statement = statement.where(Source.key.in_(source_key))  # type: ignore[attr-defined]
        elif source_key is not None:
            statement = statement.where(Source.key == source_key)
        return self.session.exec(statement.options(*options)).unique()

    def _preload_show(  # noqa: PLR0913
        self,
        show_key: str | None = None,
        show_id: uuid.UUID | None = None,
        source_key: str | None = None,
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
            if source_key is not None:
                statement = statement.where(Source.key == source_key)
        else:
            msg = "Either show_key or show_id must be provided"
            raise ValueError(msg)
        return self.session.exec(statement.options(*options)).unique()

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
        return self.session.exec(
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
        return self.session.exec(
            select(Episode).where(Episode.id == episode_id).options(*options),
        )

    def get_new_files[T: BaseFile[Any]](
        self,
        data_timestamp: datetime | None,
        file_class: type[T],
        factory: Callable[[File], T],
    ) -> list[T]:
        """Return files of `file_class` newer than `data_timestamp`.

        Ordered ascending by `data_timestamp` so callers can apply updates
        in the sequence the files were written.
        """
        if not data_timestamp:
            msg = "No data timestamp provided."
            raise ValueError(msg)

        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{file_class.__name__}/"),
                col(File.data_timestamp) > data_timestamp,
            )
            .order_by(col(File.data_timestamp).asc())
        )
        return [factory(file) for file in self.session.exec(statement).all()]

    def get_incomplete_files[T: BaseFile[Any]](
        self,
        file_class: type[T],
        factory: Callable[[File], T],
        *,
        key_prefix: str = "",
    ) -> list[T]:
        """Return files of `file_class` not yet marked "Completed" in `File.extra`."""
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{file_class.__name__}/{key_prefix}"),
                # is_distinct_from keeps rows where extra is NULL (not imported).
                col(File.extra).is_distinct_from("Completed"),
            )
            .order_by(col(File.data_timestamp).asc())
        )
        return [factory(file) for file in self.session.exec(statement).all()]
