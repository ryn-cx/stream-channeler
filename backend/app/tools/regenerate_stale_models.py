# TODO: Validate

import json
from typing import Any

from loguru import logger
from sqlmodel import Session, select

from app.database import engine, load_models
from app.files.models import File
from app.plugins.models import Plugin
from plugins.utils.base_plugin.files import GAPIListJSON, PartialGAPIJSON
from plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def _all_subclasses(base_class: type) -> set[type]:
    subclasses: set[type] = set()
    for subclass in base_class.__subclasses__():
        subclasses.add(subclass)
        subclasses |= _all_subclasses(subclass)
    return subclasses


def _plugin_package(cls: type) -> str:
    module_parts = cls.__module__.split(".")
    return module_parts[1] if len(module_parts) > 1 else module_parts[0]


def _gapi_file_classes_by_package() -> dict[str, dict[str, type[PartialGAPIJSON]]]:
    mapping: dict[str, dict[str, type[PartialGAPIJSON]]] = {}
    for file_class in _all_subclasses(PartialGAPIJSON):
        if getattr(file_class, "API_ENDPOINT", None) is None:
            continue
        mapping.setdefault(_plugin_package(file_class), {})[file_class.__name__] = (
            file_class
        )
    return mapping


def _parse_file(
    file_class: type[PartialGAPIJSON],
    raw_json: Any,  # noqa: ANN401 - Raw deserialized JSON is always Any.
    *,
    update_model: bool,
) -> None:
    endpoint = file_class.API_ENDPOINT
    if issubclass(file_class, GAPIListJSON):
        for page in raw_json:
            endpoint.parse(page, update_model=update_model)
    else:
        endpoint.parse(raw_json, update_model=update_model)


def regenerate_stale_models(session: Session) -> None:
    plugin_classes_by_key = {
        plugin_class.plugin_key(): plugin_class for plugin_class in plugins
    }
    gapi_file_classes = _gapi_file_classes_by_package()
    plugins_by_id = {
        plugin_record.id: plugin_record
        for plugin_record in session.exec(select(Plugin)).all()
    }

    # Load only the lightweight identifiers up front; each file's `content` (which
    # can be large) is fetched one at a time below so the whole corpus is never held
    # in memory at once.
    file_identifiers = session.exec(select(File.plugin_id, File.key)).all()

    regenerated_count = 0
    for plugin_id, key in file_identifiers:
        plugin_record = plugins_by_id.get(plugin_id)
        if plugin_record is None:
            continue
        plugin_class = plugin_classes_by_key.get(plugin_record.key)
        if plugin_class is None:
            continue

        file_class = gapi_file_classes.get(_plugin_package(plugin_class), {}).get(
            key.split("/", 1)[0],
        )
        if file_class is None:
            continue

        content = session.exec(
            select(File.content).where(File.plugin_id == plugin_id, File.key == key),
        ).one()
        if not content:
            continue

        try:
            raw_json = json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Could not decode {plugin_record.key}/{key}")
            continue

        try:
            _parse_file(file_class, raw_json, update_model=False)
            continue
        except Exception as error:  # noqa: BLE001 - Any parse failure means the model is stale.
            regenerated_count += 1
            logger.warning(f"Parse failed for {plugin_record.key}/{key}")

        _parse_file(file_class, raw_json, update_model=True)

    logger.info(f"Reparse completed with {regenerated_count} model regenerations")


if __name__ == "__main__":
    with Session(engine) as session:
        regenerate_stale_models(session)
