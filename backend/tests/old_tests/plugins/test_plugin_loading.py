# TODO: Validate
from app.constants import APP_FOLDER
from app.plugins.plugins.utils.manage_plugins import import_plugins, plugins

PLUGINS_FOLDER = APP_FOLDER / "plugins" / "plugins"
IGNORED_FOLDERS = {"utils", "__pycache__"}


def test_load_plugins() -> None:
    """Test that import_plugins loads all plugins from the plugins folder."""
    expected = [
        plugin.name
        for plugin in PLUGINS_FOLDER.iterdir()
        if plugin.is_dir() and plugin.name not in IGNORED_FOLDERS
    ]

    # There should be at least 1 plugin loaded
    assert expected

    import_plugins()

    plugin_names = [x.__name__ for x in plugins]
    for folder_name in expected:
        assert any(folder_name.lower() in name.lower() for name in plugin_names), (
            f"No plugin loaded for folder '{folder_name}'. Loaded: {plugin_names}"
        )
