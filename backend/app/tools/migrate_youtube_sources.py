# TODO: Validate
from loguru import logger
from sqlmodel import Session, col, select

from app.database import engine, load_models
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from plugins.utils.manage_plugins import import_plugins
from plugins.YouTube import YouTube
from plugins.YouTube.files import is_music_playlist_key
from plugins.YouTube.helpers import FREE_SOURCE_KEY, PAID_SOURCE_KEY

import_plugins()
load_models()

# The source releases used to be filed under, before they were filed under the
# same source as everything else YouTube holds.
_LEGACY_MUSIC_SOURCE_KEY = "YouTube Music"


# TODO: Validate
def _youtube_sources(session: Session) -> list[Source]:
    statement = (
        select(Source)
        .join(Plugin)
        .join(User, col(Plugin.user_id) == User.id)
        .where(User.email == PLUGIN_USER_EMAIL, col(Plugin.key) == YouTube.plugin_key())
    )
    return list(session.exec(statement).unique().all())


# TODO: Validate
def move_standalone_shows(session: Session, plugin: YouTube) -> None:
    kept_keys = {YouTube.plugin_key(), FREE_SOURCE_KEY, PAID_SOURCE_KEY}
    legacy_sources = [
        source for source in _youtube_sources(session) if source.key not in kept_keys
    ]
    if not legacy_sources:
        return

    for source in legacy_sources:
        for show in source.shows:
            target = plugin.paid_or_free_source(show.key)
            if Show.get(session, target, show.key):
                logger.info("Deleting {}, already in {}", show.key, target.key)
                show.soft_delete()
                continue
            logger.info("Moving {} to {}", show.key, target.key)
            show.source_id = target.id
        source.soft_delete(recursive=False)


# TODO: Validate
def merge_music_source(session: Session, plugin: YouTube) -> None:
    music_sources = [
        source
        for source in _youtube_sources(session)
        if source.key == _LEGACY_MUSIC_SOURCE_KEY
    ]
    for source in music_sources:
        for show in source.shows:
            if Show.get(session, plugin.source, show.key):
                logger.info("Deleting {}, already in {}", show.key, plugin.source.key)
                show.soft_delete()
                continue
            logger.info("Moving {} to {}", show.key, plugin.source.key)
            show.source_id = plugin.source.id
        source.soft_delete(recursive=False)


# TODO: Validate
def reimport_releases(session: Session, plugin: YouTube) -> None:
    statement = (
        select(Season)
        .join(Show)
        .join(Source)
        .join(Plugin)
        .where(
            col(Plugin.key) == YouTube.plugin_key(),
            col(Season.deleted_at).is_(None),
        )
    )
    release_keys = [
        season.key
        for season in session.exec(statement).unique().all()
        if is_music_playlist_key(season.key) and season.show.key != season.key
    ]
    for release_key in release_keys:
        url = YouTube.build_url(f"playlist?list={release_key}")
        logger.info("Reimporting {}", url)
        plugin.import_url(url)
        session.commit()


# TODO: Validate
def migrate_youtube_sources() -> None:
    with Session(engine) as session:
        plugin = YouTube(session)
        merge_music_source(session, plugin)
        session.commit()
        move_standalone_shows(session, plugin)
        session.commit()
        reimport_releases(session, plugin)
        session.commit()


if __name__ == "__main__":
    migrate_youtube_sources()
    logger.info("Migration completed")
