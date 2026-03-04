from sqlmodel import Session

from app.episodes.schemas import EpisodeInput
from app.plugins.models import Plugin
from app.plugins.schemas import FileInput, PluginInput
from app.seasons.schemas import SeasonInput
from app.shows.schemas import ShowInput
from app.sources.schemas import SourceInput
from tests.utils.utils import build_random_model


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
