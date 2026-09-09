# TODO: Validate

from collections.abc import Sequence

from loguru import logger
from sqlmodel import Session, col
from tqdm import tqdm

from app.channels.channel_scope import in_a_user_channel
from app.database import engine, load_models
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.titles.models import Title
from app.titles.service.website_linking import link_title_to_websites
from plugins.utils.manage_plugins import import_plugins

import_plugins()
load_models()


# TODO: Validate
def _tmdb_titles_due_for_linking(session: Session) -> Sequence[Title]:
    return session.exec(
        Title.select_with_plugin()
        .where(col(Title.link_status).is_(None))
        .where(Plugin.key == TMDB_PLUGIN_KEY)
        .order_by(in_a_user_channel().desc(), col(Title.modified_at).asc()),
    ).all()


# TODO: Validate
def link_tmdb_titles_to_websites(session: Session) -> None:
    titles = _tmdb_titles_due_for_linking(session)

    progress = tqdm(titles, unit="title")
    for title in progress:
        progress.set_description(title.name or title.key)
        logger.info(f"[TMDB] Linking to websites: {title.name or title.key}")
        try:
            link_title_to_websites(session, title)
        except Exception:  # noqa: BLE001
            logger.exception(f"[TMDB] Failed to link {title.key} to websites")
            session.rollback()
            title.link_status = "Failed"
        else:
            title.link_status = "Linked"
        session.add(title)
        session.commit()


if __name__ == "__main__":
    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))

    with Session(engine) as session:
        link_tmdb_titles_to_websites(session)

    logger.info("Linking completed")
