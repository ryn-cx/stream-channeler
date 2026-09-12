# TODO: Validate


from loguru import logger
from sqlmodel import Session, col
from tqdm import tqdm

from app.channels.channel_scope import in_a_user_channel
from app.database import engine, load_models
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.titles.service.linking import link_new_title_to_tmdb
from plugins.utils.manage_plugins import import_plugins

import_plugins()
load_models()


# TODO: Validate
def link_titles_to_tmdb(session: Session) -> None:
    unlinked_titles = session.exec(
        Title.select_with_plugin()
        .where(col(Title.link_status).is_(None))
        .where(col(Source.link_to_tmdb).is_(True))
        .where(Plugin.key != TMDB_PLUGIN_KEY)
        .order_by(in_a_user_channel().desc(), col(Title.modified_at).asc()),
    ).all()

    progress = tqdm(unlinked_titles, unit="title")
    for title in progress:
        progress.set_description(f"{title.source.key}: {title.name or title.key}")
        try:
            link_new_title_to_tmdb(session, title)
        except Exception:  # noqa: BLE001
            logger.exception(f"Failed to link {title.key} to TMDB")
            session.rollback()
            title.link_status = "Failed"
            session.add(title)
            session.commit()


if __name__ == "__main__":
    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))

    with Session(engine) as session:
        link_titles_to_tmdb(session)

    logger.info("Linking completed")
