# TODO: Validate

from sqlalchemy import ColumnElement, func


# TODO: Validate
def watch_identifier(plugin_key: str, key: str) -> str:
    """Return what a `Watch` of the episode `plugin_key` keyed as `key` is of.

    A plugin's own key names the media itself rather than one row for it — a
    YouTube episode is keyed by its video id, which is the same id wherever that
    video turns up — so namespacing it by the plugin is enough to say that two
    rows are of the same media.
    """
    return f"{plugin_key} {key}"


# TODO: Validate
def key_issuer(key_column: ColumnElement[str]) -> ColumnElement[str]:
    """Return who issued the record `key_column` names."""
    return func.split_part(key_column, " ", 1)


# TODO: Validate
def same_issuer_clause(
    first: ColumnElement[str],
    second: ColumnElement[str],
) -> ColumnElement[bool]:
    return key_issuer(first) == key_issuer(second)
