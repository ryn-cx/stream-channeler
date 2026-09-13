# TODO: Validate
"""Narrow a tool's run to one plugin or one of its sources.

A tool walks the whole library by default. `--plugin` and `--source` are what
cut that down to the part being worked on, so a plugin that has just changed can
be re-run on its own rather than behind everything else. They name the keys the
records carry, and they stack: `--plugin Crunchyroll --source Music` is the music
source of that plugin and nothing else.
"""

from argparse import ArgumentParser
from dataclasses import dataclass

from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col

from app.plugins.models import Plugin
from app.sources.models import Source


# TODO: Validate
@dataclass(frozen=True)
class PluginSelection:
    plugin_key: str | None = None
    source_key: str | None = None


# TODO: Validate
def add_selection_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--plugin",
        default=None,
        help="Only act on records from the plugin with this key.",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Only act on records from the source with this key.",
    )


# TODO: Validate
def parse_selection(description: str) -> PluginSelection:
    parser = ArgumentParser(description=description)
    add_selection_arguments(parser)
    arguments = parser.parse_args()
    return PluginSelection(arguments.plugin, arguments.source)


# TODO: Validate
def selection_clauses(selection: PluginSelection) -> list[ColumnElement[bool]]:
    """Return what a statement joined to `Source` and `Plugin` filters on.

    Nothing is returned when neither argument was given, which is what leaves a
    run that named no plugin covering everything.
    """
    clauses: list[ColumnElement[bool]] = []
    if selection.plugin_key is not None:
        clauses.append(col(Plugin.key) == selection.plugin_key)
    if selection.source_key is not None:
        clauses.append(col(Source.key) == selection.source_key)
    return clauses


# TODO: Validate
def selection_description(selection: PluginSelection) -> str:
    """Return what the run covers, for the line a tool logs when it starts."""
    named = [
        f"{label} {key}"
        for label, key in (
            ("plugin", selection.plugin_key),
            ("source", selection.source_key),
        )
        if key is not None
    ]
    return " and ".join(named) if named else "every plugin"
