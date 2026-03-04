# TODO: Validate

import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.plugins.models import Plugin
from app.plugins.schemas import FileInput, PluginInput
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.sources.schemas import SourceInput
from app.utils import tz_datetime
from app.watches.models import EpisodeWatch
from tests.old_tests.utils.utils import build_random_model


def create_random_plugin(db: Session, user_id: uuid.UUID | None = None) -> Plugin:
    plugin_input = build_random_model(PluginInput)
    plugin_input.user_id = user_id
    plugin = plugin_input.upsert(db, None)
    db.commit()
    return plugin


def create_random_source(
    db: Session,
    plugin: Plugin | None = None,
    user_id: uuid.UUID | None = None,
) -> Source:
    if plugin is None:
        plugin = create_random_plugin(db, user_id)
    source = build_random_model(SourceInput).upsert(plugin, None)
    db.commit()
    return source


def create_random_show(
    db: Session,
    source: Source | None = None,
    user_id: uuid.UUID | None = None,
) -> Show:
    if source is None:
        source = create_random_source(db, user_id=user_id)
    show = build_random_model(ShowInput).upsert(source, None)
    db.commit()
    return show


def create_random_season(
    db: Session,
    show: Show | None = None,
    user_id: uuid.UUID | None = None,
) -> Season:
    if show is None:
        show = create_random_show(db, user_id=user_id)
    season = build_random_model(SeasonInput).upsert(show, None)
    db.commit()
    return season


def create_random_episode(
    db: Session,
    season: Season | None = None,
    user_id: uuid.UUID | None = None,
) -> Episode:
    if season is None:
        season = create_random_season(db, user_id=user_id)
    episode = build_random_model(EpisodeInput).upsert(season, None)
    db.commit()
    return episode


def create_random_watch(
    db: Session,
    user_id: uuid.UUID,
    episode: Episode | None = None,
) -> EpisodeWatch:
    if episode is None:
        episode = create_random_episode(db)

    episode_watch = EpisodeWatch(
        user_id=user_id,
        episode_id=episode.id,
        watch_date=tz_datetime.now(),
        verified=False,
    )
    db.add(episode_watch)
    db.commit()

    return episode_watch


# PLR0913 - More parameters makes this more flexible.
def create_random_heirarchy(  # noqa: PLR0913
    db: Session,
    plugin_count: int = 0,
    file_count: int = 0,
    source_count: int = 0,
    show_count: int = 0,
    season_count: int = 0,
    episode_count: int = 0,
    *,
    default_count: int = 1,
) -> list[Plugin]:
    """Create a full hierarchy of Plugin, Source, Show, Season, Episode, File."""
    plugins: list[Plugin] = []

    for _ in range(plugin_count or default_count):
        plugin = build_random_model(
            PluginInput,
            user_id=None,
            deleted_at=None,
        ).upsert(db, None)
        plugins.append(plugin)

        for _ in range(file_count or default_count):
            build_random_model(FileInput, deleted_at=None).upsert(plugin, None)

        for _ in range(source_count or default_count):
            source = build_random_model(
                SourceInput,
                deleted_at=None,
            ).upsert(plugin, None)

            for _ in range(show_count or default_count):
                show = build_random_model(
                    ShowInput,
                    deleted_at=None,
                ).upsert(source, None)

                for _ in range(season_count or default_count):
                    season = build_random_model(
                        SeasonInput,
                        deleted_at=None,
                    ).upsert(show, None)

                    for _ in range(episode_count or default_count):
                        build_random_model(
                            EpisodeInput,
                            deleted_at=None,
                        ).upsert(season, None)
    db.commit()
    return plugins
