# TODO: Validate
from typing import Any

from loguru import logger
from sqlmodel import Session

from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.constants import OUTDATED_STATUS

logger = logger.bind(source="updater")


# TODO: Validate
def update_record(
    session: Session,
    plugin_instance: AbstractPlugin,
    plugin_key: str,
    item: Any,  # noqa: ANN401
) -> bool:
    media_type_name = type(item).__name__.lower()
    update_method_name = f"update_{media_type_name}"
    try:
        update = getattr(plugin_instance, update_method_name)
        if isinstance(item, Source):
            update(item, item.update_at)
        else:
            update(item)

        if item.status == OUTDATED_STATUS:
            item.status = None

        log_msg = f"[{plugin_key}] Successfully updated {media_type_name}: {item.key}"
        logger.info(log_msg)

        session.commit()
    except Exception as error:
        log_msg = f"[{plugin_key}] Failed to update {media_type_name}: {item.key}"
        logger.exception(log_msg)
        # Roll back partial changes, then let the plugin decide how to
        # reschedule the failed item.
        session.rollback()
        session.refresh(item)
        failure_method_name = f"on_update_{media_type_name}_failure"
        try:
            getattr(plugin_instance, failure_method_name)(item, error)
        except Exception:  # noqa: BLE001 - The plugin re-raised its default.
            # Set update_at to the maximum possible value to avoid retrying
            # the update until the issue is resolved.
            item.update_at = tz_datetime.max()
        session.commit()
        return False
    return True
