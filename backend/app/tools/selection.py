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
    plugin_keys: tuple[str, ...] = ()
    source_keys: tuple[str, ...] = ()


# TODO: Validate
def add_selection_arguments(
    parser: ArgumentParser,
    *,
    include_source: bool = True,
) -> None:
    parser.add_argument(
        "--plugin",
        nargs="+",
        default=None,
        help="Only act on records from the plugins with these keys.",
    )
    if include_source:
        parser.add_argument(
            "--source",
            nargs="+",
            default=None,
            help="Only act on records from the sources with these keys.",
        )


# TODO: Validate
def parse_selection(
    description: str,
    *,
    include_source: bool = True,
) -> PluginSelection:
    parser = ArgumentParser(description=description)
    add_selection_arguments(parser, include_source=include_source)
    arguments = parser.parse_args()
    source_keys = arguments.source if include_source else None
    return PluginSelection(tuple(arguments.plugin or ()), tuple(source_keys or ()))


# TODO: Validate
def selection_clauses(selection: PluginSelection) -> list[ColumnElement[bool]]:
    """Return what a statement joined to `Source` and `Plugin` filters on.

    Nothing is returned when neither argument was given, which is what leaves a
    run that named no plugin covering everything.
    """
    clauses: list[ColumnElement[bool]] = []
    if selection.plugin_keys:
        clauses.append(col(Plugin.key).in_(selection.plugin_keys))
    if selection.source_keys:
        clauses.append(col(Source.key).in_(selection.source_keys))
    return clauses


# TODO: Validate
def selection_description(selection: PluginSelection) -> str:
    """Return what the run covers, for the line a tool logs when it starts."""
    named = [
        f"{label}{'s' if len(keys) > 1 else ''} {', '.join(keys)}"
        for label, keys in (
            ("plugin", selection.plugin_keys),
            ("source", selection.source_keys),
        )
        if keys
    ]
    return " and ".join(named) if named else "every plugin"
