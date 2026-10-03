# TODO: Validate
"""Narrow a tool's run to one plugin or one of its sources.

A tool walks the whole library by default. `--plugin` and `--source` are what
cut that down to the part being worked on, so a plugin that has just changed can
be re-run on its own rather than behind everything else. They name the keys the
records hold, and they stack: `--plugin Crunchyroll --source Music` is the music
source of that plugin and nothing else.
"""

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass

from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col

from app.channels.channel_scope import in_a_user_channel
from app.plugins.models import Plugin
from app.sources.models import Source


# TODO: Validate
@dataclass(frozen=True)
class PluginSelection:
    plugin_keys: tuple[str, ...] = ()
    source_keys: tuple[str, ...] = ()
    user_channels_only: bool = False


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
    else:
        parser.set_defaults(source=None)
    parser.add_argument(
        "--user-channels-only",
        action="store_true",
        help="Only act on records that are in a channel owned by a real user.",
    )


# TODO: Validate
def selection_from_arguments(arguments: Namespace) -> PluginSelection:
    return PluginSelection(
        tuple(arguments.plugin or ()),
        tuple(arguments.source or ()),
        user_channels_only=arguments.user_channels_only,
    )


# TODO: Validate
def add_threads_argument(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--threads",
        type=int,
        default=1,
        help="How many records to work on at once.",
    )


# TODO: Validate
def parse_selection(
    description: str,
    *,
    include_source: bool = True,
) -> PluginSelection:
    parser = ArgumentParser(description=description)
    add_selection_arguments(parser, include_source=include_source)
    return selection_from_arguments(parser.parse_args())


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
def user_channel_clauses(selection: PluginSelection) -> list[ColumnElement[bool]]:
    return [in_a_user_channel()] if selection.user_channels_only else []


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
    covered = " and ".join(named) if named else "every plugin"
    if selection.user_channels_only:
        covered = f"{covered}, limited to records in user channels"
    return covered
