# TODO: Validate

import importlib
import json
import os
from pathlib import Path
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


# TODO: Validate
def _all_subclasses(base_class: type) -> set[type]:
    subclasses: set[type] = set()
    for subclass in base_class.__subclasses__():
        subclasses.add(subclass)
        subclasses |= _all_subclasses(subclass)
    return subclasses


# TODO: Validate
def _plugin_package(cls: type) -> str:
    module_parts = cls.__module__.split(".")
    return module_parts[1] if len(module_parts) > 1 else module_parts[0]


# TODO: Validate
def _gapi_file_classes_by_package() -> dict[str, dict[str, type[PartialGAPIJSON]]]:
    mapping: dict[str, dict[str, type[PartialGAPIJSON]]] = {}
    for file_class in _all_subclasses(PartialGAPIJSON):
        if getattr(file_class, "API_ENDPOINT", None) is None:
            continue
        mapping.setdefault(_plugin_package(file_class), {})[file_class.__name__] = (
            file_class
        )
    return mapping


# TODO: Validate
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


# TODO: Validate
def _scraper_package(file_class: type[PartialGAPIJSON]) -> str:
    endpoint = file_class.API_ENDPOINT
    endpoint_class = endpoint if isinstance(endpoint, type) else type(endpoint)
    return endpoint_class.__module__.split(".")[0]


# TODO: Validate
def _copy_corpus(scraper_package: str, scrapers_root: Path) -> int:
    # A scraper's regeneration corpus is `<package>/_files`; mirror it into the
    # scraper's source layout, matching how `rip_files` lays it out on disk.
    package_file = importlib.import_module(scraper_package).__file__
    if package_file is None:
        return 0
    files_root = Path(package_file).parent / "_files"
    if not files_root.is_dir():
        return 0

    destination_root = (
        scrapers_root
        / scraper_package.replace("_", "-")
        / "src"
        / scraper_package
        / "_files"
    )
    copied_count = 0
    for source in files_root.rglob("*"):
        if source.is_dir():
            continue
        destination = destination_root / source.relative_to(files_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        copied_count += 1
    return copied_count


# TODO: Validate
def regenerate_stale_models(session: Session, scrapers_root: Path) -> None:
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
        except Exception:  # noqa: BLE001 - Any parse failure means the model is stale.
            regenerated_count += 1
            logger.warning(f"Parse failed for {plugin_record.key}/{key}")

        _parse_file(file_class, raw_json, update_model=True)

    # Copy every scraper's regeneration corpus out into the run folder so the
    # updated files and models can be committed back to the scraper repos.
    scraper_packages = {
        _scraper_package(file_class)
        for classes in gapi_file_classes.values()
        for file_class in classes.values()
    }
    copied_count = 0
    for scraper_package in sorted(scraper_packages):
        copied_count += _copy_corpus(scraper_package, scrapers_root)

    logger.info(
        f"Regenerated {regenerated_count} models; "
        f"copied {copied_count} corpus files to {scrapers_root}",
    )


if __name__ == "__main__":
    scrapers_directory = Path(os.environ.get("SCRAPERS_DIR", "scrapers"))
    with Session(engine) as session:
        regenerate_stale_models(session, scrapers_directory)
