# TODO: Validate

import time
from datetime import timedelta

from loguru import logger
from sqlmodel import Session, col, select

from app.channels.models import Channel
from app.database import engine, load_models
from app.log import configure_logging
from app.users.models import User
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import import_plugins, plugins

logger = logger.bind(source="update_channels")

import_plugins()
load_models()


# TODO: Validate
def _outdated_channels_by_plugin(
    session: Session,
) -> dict[type[AbstractPlugin], list[Channel]]:
    plugin_classes_by_email = {
        plugin_class.plugin_name().lower(): plugin_class for plugin_class in plugins
    }
    rows = session.exec(
        select(Channel, User.email)
        .join(User, col(Channel.user_id) == col(User.id))
        .where(col(Channel.update_at) <= tz_datetime.now())
        .order_by(col(Channel.update_at).asc()),
    ).all()
    by_plugin: dict[type[AbstractPlugin], list[Channel]] = {}
    for channel, email in rows:
        if plugin_class := plugin_classes_by_email.get(email.lower()):
            by_plugin.setdefault(plugin_class, []).append(channel)
    return by_plugin


# TODO: Validate
def update_channels(session: Session) -> None:
    for plugin_class, channels in _outdated_channels_by_plugin(session).items():
        plugin = plugin_class(session)
        for channel in channels:
            log_msg = f"[{plugin_class.plugin_name()}] Updating channel: {channel.name}"
            logger.info(log_msg)
            plugin.update_channel(channel)
            if channel.update_at is None:
                channel.update_at = tz_datetime.now() + timedelta(days=1)
            session.commit()


# TODO: Validate
def run_forever() -> None:
    while True:
        with Session(engine) as session:
            update_channels(session)
        time.sleep(60 * 60)


if __name__ == "__main__":
    configure_logging()
    run_forever()
