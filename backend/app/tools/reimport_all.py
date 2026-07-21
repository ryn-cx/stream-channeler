# TODO: Validate

from collections.abc import Sequence

from loguru import logger
from sqlmodel import Session, col

from app.database import engine, load_models
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def _reimport_shows(session: Session, shows: Sequence[Show]) -> None:
    plugin_classes_by_key = {plugin.plugin_key(): plugin for plugin in plugins}
    for show in shows:
        plugin_class = plugin_classes_by_key[show.source.plugin.key]
        plugin_instance = plugin_class(session)
        plugin_instance.update_show(show, force=True)
        session.commit()


def reimport_all_shows(session: Session) -> None:
    shows = session.exec(
        Show.select_with_plugin()
        .join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
        .where(
            User.email == PLUGIN_USER_EMAIL,
        ),
    ).all()

    _reimport_shows(session, shows)


def reimport_shows_missing_episode_identifier(session: Session) -> None:
    shows = session.exec(
        Show.select_with_plugin()
        .join(User, Plugin.user_id == User.id)  # type: ignore[arg-type]
        .join(Season, col(Season.show_id) == Show.id)
        .join(Episode, col(Episode.season_id) == Season.id)
        .where(
            User.email == PLUGIN_USER_EMAIL,
            col(Episode.episode_identifier)
            == col(Plugin.key) + " " + col(Episode.key),
        )
        .distinct(),
    ).all()

    _reimport_shows(session, shows)


if __name__ == "__main__":
    with Session(engine) as session:
        reimport_shows_missing_episode_identifier(session)

    logger.info("Reimport completed")
