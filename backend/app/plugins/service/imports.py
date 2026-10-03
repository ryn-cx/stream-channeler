# TODO: Validate

from sqlmodel import Session, col, select

from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginSupportInformation,
    PluginURLMatch,
)
from plugins.utils.manage_plugins import sorted_plugins


# TODO: Validate
def hidden_plugin_keys(session: Session) -> set[str]:
    """Return the keys of the plugins kept out of what a normal `User` is shown."""
    return set(
        session.exec(select(Plugin.key).where(col(Plugin.hidden).is_(True))).all(),
    )


# TODO: Validate
def import_watch_history_information(
    session: Session,
) -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    hidden = hidden_plugin_keys(session)
    return [
        PluginImportWatchHistoryInformation(
            plugin_key=plugin_cls.plugin_name(),
            file_extension=plugin_cls.import_watch_history_file_extension,
            instructions=plugin_cls.import_watch_history_instructions(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("import_watch_history")
        and plugin_cls.plugin_name() not in hidden
    ]


# TODO: Validate
def import_url_information(session: Session) -> list[PluginImportURLInformation]:
    """Return information about the plugins offered as ways to add by URL.

    A plugin that imports URLs but is only reached through another one is left
    out. `match-url` still resolves its URLs, so one a `User` pastes anyway is
    imported rather than rejected.
    """
    hidden = hidden_plugin_keys(session)
    return [
        PluginImportURLInformation(
            name=plugin_cls.plugin_name(),
            instructions=plugin_cls.import_url_instructions(),
            favicon_url=plugin_cls.favicon_url(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("validate_and_import_url")
        and plugin_cls.plugin_name() not in hidden
    ]


# TODO: Validate
def match_url(session: Session, url: str) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    hidden = hidden_plugin_keys(session)
    for plugin_cls in sorted_plugins():
        if (
            plugin_cls.implements("validate_and_import_url")
            and plugin_cls.is_valid_url_format(url)
            and plugin_cls.plugin_name() not in hidden
        ):
            return PluginURLMatch(matched=True, plugin_key=plugin_cls.plugin_name())
    return PluginURLMatch(matched=False)


# TODO: Validate
def support_information() -> list[PluginSupportInformation]:
    information: list[PluginSupportInformation] = []
    for plugin_cls in sorted_plugins():
        catalog_support = plugin_cls.CATALOG_SUPPORT
        if catalog_support is None:
            continue
        information.append(
            PluginSupportInformation(
                name=plugin_cls.plugin_name(),
                favicon_url=plugin_cls.favicon_url(),
                catalog_support=catalog_support,
                known_issues=plugin_cls.KNOWN_ISSUES,
            ),
        )
    return information
