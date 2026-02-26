# TODO: Validate

import uuid

from sqlmodel import Session

from app.media.models import Episode, EpisodeWatch, Plugin, Season, Show, Source
from app.media.schemas import (
    EpisodeInput,
    FileInput,
    PluginInput,
    SeasonInput,
    ShowInput,
    SourceInput,
)
from app.utils import tz_datetime
from tests.utils.utils import (
    random_lower_string,
)


def get_random_plugin_input() -> PluginInput:
    return PluginInput(
        key=random_lower_string(),
        name=random_lower_string(),
        data_timestamp=tz_datetime.now(),
    )


def get_random_source_input() -> SourceInput:
    return SourceInput(
        key=random_lower_string(),
        name=random_lower_string(),
        data_timestamp=tz_datetime.now(),
    )


def get_random_file_input() -> FileInput:
    return FileInput(
        key=random_lower_string(),
        content=random_lower_string(),
        data_timestamp=tz_datetime.now(),
    )


def get_random_show_input() -> ShowInput:
    return ShowInput(
        key=random_lower_string(),
        name=random_lower_string(),
        data_timestamp=tz_datetime.now(),
    )


def get_random_season_input() -> SeasonInput:
    return SeasonInput(
        key=random_lower_string(),
        data_timestamp=tz_datetime.now(),
    )


def get_random_episode_input() -> EpisodeInput:
    return EpisodeInput(
        key=random_lower_string(),
        url=random_lower_string(),
        data_timestamp=tz_datetime.now(),
    )


def get_random_plugin(db: Session) -> Plugin:
    plugin_input = get_random_plugin_input()
    return plugin_input.upsert(db)


def get_random_source(db: Session, plugin: Plugin | None = None) -> Source:
    if plugin is None:
        plugin = get_random_plugin(db)
    source_input = get_random_source_input()
    return source_input.upsert(plugin)


def get_random_show(db: Session, source: Source | None = None) -> Show:
    if source is None:
        source = get_random_source(db)
    show_input = get_random_show_input()
    return show_input.upsert(source)


def get_random_season(db: Session, show: Show | None = None) -> Season:
    if show is None:
        show = get_random_show(db)
    season_input = get_random_season_input()
    return season_input.upsert(show)


def get_random_episode(db: Session, season: Season | None = None) -> Episode:
    if season is None:
        season = get_random_season(db)
    episode_input = get_random_episode_input()
    return episode_input.upsert(season)


def get_random_episode_watch(
    db: Session,
    user_id: uuid.UUID,
    episode: Episode | None = None,
) -> EpisodeWatch:
    if episode is None:
        episode = get_random_episode(db)

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
        plugin_input = get_random_plugin_input()
        plugin = plugin_input.upsert(db, None)
        plugins.append(plugin)

        for _ in range(file_count or default_count):
            file_input = get_random_file_input()
            file_input.upsert(db, plugin, None)

        for _ in range(source_count or default_count):
            source_input = get_random_source_input()
            source = source_input.upsert(plugin, None)

            for _ in range(show_count or default_count):
                show_input = get_random_show_input()
                show = show_input.upsert(source, None)

                for _ in range(season_count or default_count):
                    season_input = get_random_season_input()
                    season = season_input.upsert(show, None)

                    for _ in range(episode_count or default_count):
                        episode_input = get_random_episode_input()
                        episode_input.upsert(season, None)
    db.commit()
    return plugins
