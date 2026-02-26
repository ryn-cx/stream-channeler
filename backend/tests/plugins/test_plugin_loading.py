# TODO: Validate
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest

from app.constants import APP_FOLDER
from app.plugins.utils.manage_plugins import import_plugins, plugins


@pytest.fixture
def dummy_file_plugin() -> Generator[Path]:
    dummy_file_path = APP_FOLDER / "plugins/dummy_file_plugin.py"
    dummy_file_content = """from app.plugins.utils.abstract_plugin import AbstractPlugin
class DummyFilePlugin(AbstractPlugin):
    pass"""
    dummy_file_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_file_path.write_text(dummy_file_content)

    yield dummy_file_path

    if dummy_file_path.exists():
        dummy_file_path.unlink()


@pytest.fixture
def dummy_folder_plugin() -> Generator[Path]:
    plugin_folder = APP_FOLDER / "plugins/dummy_folder_plugin"
    plugin_file = plugin_folder / "dummy.py"
    init_file = plugin_folder / "__init__.py"

    plugin_file_content = (
        "from app.plugins.utils.abstract_plugin import AbstractPlugin\n"
        "class DummyFolderPlugin(AbstractPlugin):\n"
        "    pass"
    )
    init_file_content = "from .dummy import DummyFolderPlugin\n"

    plugin_file.parent.mkdir(parents=True, exist_ok=True)
    plugin_file.write_text(plugin_file_content)
    init_file.write_text(init_file_content)

    yield plugin_folder

    if plugin_folder.exists():
        shutil.rmtree(plugin_folder, ignore_errors=True)


def test_load_folder_plugins(
    dummy_folder_plugin: Path,  # noqa: ARG001 - Fixture
) -> None:
    """Test that the import_plugins function loads plugins from a folder."""
    import_plugins()

    # Check that the plugin was registered using its class name because class names
    # avoid having to manually import the plugins which defeats the purpose of this
    # test.
    plugin_names = [x.__name__ for x in plugins]
    assert "DummyFolderPlugin" in plugin_names, (
        f"DummyFolderPlugin not found in {plugin_names}"
    )


def test_load_file_plugins(
    dummy_file_plugin: Path,  # noqa: ARG001 - Fixture
) -> None:
    """Test that the import_plugins function loads plugins from a file."""
    import_plugins()

    # Check that the plugin was registered using its class name because class names
    # avoid having to manually import the plugins which defeats the purpose of this
    # test.
    plugin_names = [x.__name__ for x in plugins]
    assert "DummyFilePlugin" in plugin_names, (
        f"DummyFilePlugin not found in {plugin_names}"
    )
