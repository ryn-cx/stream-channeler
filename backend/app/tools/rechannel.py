# TODO: Validate
"""Sort every title onto the automatic channels it belongs on.

A plugin sorts a title into its channels as the title is imported, so a plugin
that changes how it sorts leaves every title imported before the change where it
was. This walks the titles again and sorts each one with the plugin as it stands
now, which is how a restructured plugin is applied to a library it has already
imported.

Nothing is imported here. A title is put into its channels' queues, and the
import queue is what turns a queued URL into the episodes on a channel.
"""

from loguru import logger
from sqlmodel import Session, col
from tqdm import tqdm

from app.database import engine, load_models
from app.plugins.models import Plugin
from app.titles.models import Title
from app.tools.selection import (
    PluginSelection,
    parse_selection,
    selection_clauses,
    selection_description,
)
from plugins.utils.base_plugin.channels import BaseChannelMixin
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


# TODO: Validate
def rechannel_titles(
    session: Session,
    selection: PluginSelection | None = None,
) -> None:
    selection = selection or PluginSelection()
    channel_plugins_by_key = {
        plugin.plugin_name(): plugin
        for plugin in plugins
        if issubclass(plugin, BaseChannelMixin)
    }
    listed = session.exec(
        Title.select_with_plugin_eager()
        .where(col(Title.deleted_at).is_(None))
        .where(*selection_clauses(selection))
        .order_by(col(Title.modified_at).asc()),
    ).all()

    plugin_instances: dict[str, BaseChannelMixin] = {}
    progress = tqdm(listed, unit="title")
    for title in progress:
        plugin_key = title.source.plugin.key
        progress.set_description(f"[{plugin_key}] {title.name or title.key}")

        # A plugin that is not installed, and one that writes no channels, both
        # leave the title where it is rather than ending the run.
        plugin_class = channel_plugins_by_key.get(plugin_key)
        if plugin_class is None:
            continue

        if plugin_key not in plugin_instances:
            plugin_instances[plugin_key] = plugin_class(
                session,
                Plugin.get_one(session, plugin_key),
            )
        try:
            plugin_instances[plugin_key].add_title_to_plugin_channels(title)
        except Exception:  # noqa: BLE001 - one title must not end the whole run.
            logger.exception(f"Failed to sort {title.key} onto its channels")
            session.rollback()
            continue
        session.commit()


if __name__ == "__main__":
    selected = parse_selection(
        "Sort every title onto the automatic channels it belongs on.",
    )

    logger.remove()
    logger.add(lambda message: tqdm.write(message, end=""))
    logger.info(f"Rechannelling {selection_description(selected)}")

    with Session(engine) as session:
        rechannel_titles(session, selected)

    logger.info("Rechannelling completed")
