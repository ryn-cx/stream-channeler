# TODO: Validate
"""The whole database written down as the text two runs compare."""

import difflib
import json
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, Table
from sqlalchemy import select as sqlalchemy_select
from sqlmodel import Session, SQLModel

EXCLUDED_TABLES = frozenset({"file", "user"})
"""The tables the dump leaves out.

The stored test files are put into `file` before a test runs, so the table says
what the store holds rather than what the run did, and topping the store up for
one test would leave every other test's recording out of date.

`user` is the account every plugin runs as and nothing a run produces. What is
stored of it is a password hash, which is salted afresh every time it is written
and so is a different value on every run no matter that the password never
changed.

An excluded table is still read, since a row that is dumped can point at one of
its rows and what an id points at is written as that row's key. Only the columns
that name a row are read, the content of a stored file being no use to anybody
and a great deal of it.
"""

_ID_COLUMN = "id"

_KEY_COLUMNS = ("key", "email", "name")
"""What a row is named by, in the order they are looked for.

The key is what every media row is named by. `email` is the user's key by
another name, and `name` is what is left for a row the user named themselves.
"""

_LINK_SEPARATOR = "+"
"""What joins the keys of the rows a link row is the link between."""

type RowValues = dict[str, Any]
type TableRows = dict[str, list[RowValues]]
type RowsById = dict[uuid.UUID, tuple[Table, RowValues]]
type KeyById = dict[uuid.UUID, str]


# TODO: Validate
def _dump_value(value: object, rows_by_id: RowsById, keys: KeyById) -> object:
    """Return `value` as something JSON holds and two runs write the same way."""
    if isinstance(value, uuid.UUID):
        return _key_for(value, rows_by_id, keys)
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return value


# TODO: Validate
def _key_for(row_id: uuid.UUID, rows_by_id: RowsById, keys: KeyById) -> str:
    """Return the key of the row `row_id` points at.

    An id is generated afresh on every run, so an id written down as it is says
    nothing two runs can compare. Every row has a key that says the same thing
    and stays put, so what an id points at is written as that row's key, which
    leaves an id pointing at the wrong row readable as the wrong name rather
    than as one meaningless value against another.
    """
    if row_id in keys:
        return keys[row_id]
    table, row = rows_by_id[row_id]
    keys[row_id] = _row_key(table, row, rows_by_id, keys)
    return keys[row_id]


# TODO: Validate
def _row_key(
    table: Table,
    row: RowValues,
    rows_by_id: RowsById,
    keys: KeyById,
) -> str:
    """Return what names one row of `table`."""
    key_column = next((name for name in _KEY_COLUMNS if name in table.columns), None)
    if key_column is not None:
        return str(row[key_column])
    # A row that is nothing but a link between two others carries no key of its
    # own, so it is named by the keys of the rows it links.
    return _LINK_SEPARATOR.join(
        str(_dump_value(row[column.name], rows_by_id, keys))
        for column in table.columns
        if column.foreign_keys
    )


# TODO: Validate
def _naming_columns(table: Table) -> list[Column[Any]]:
    """Return the columns that a row of `table` is read back by its key from."""
    key_column = next((name for name in _KEY_COLUMNS if name in table.columns), None)
    named = (
        [table.columns[key_column]]
        if key_column is not None
        else [column for column in table.columns if column.foreign_keys]
    )
    return [table.columns[_ID_COLUMN], *named]


# TODO: Validate
def _read_tables(session: Session) -> list[tuple[Table, list[RowValues]]]:
    """Read every row of every table, an excluded one by its names alone."""
    tables: list[tuple[Table, list[RowValues]]] = []
    for table in SQLModel.metadata.sorted_tables:
        columns = (
            _naming_columns(table)
            if table.name in EXCLUDED_TABLES
            else [*table.columns]
        )
        tables.append(
            (
                table,
                [
                    dict(row._mapping)  # pyright: ignore[reportPrivateUsage] # noqa: SLF001
                    for row in session.execute(sqlalchemy_select(*columns))
                ],
            ),
        )
    return tables


# TODO: Validate
def _rows_by_id(tables: list[tuple[Table, list[RowValues]]]) -> RowsById:
    """Return every row an id in the dump can point at, by that id."""
    return {
        row[_ID_COLUMN]: (table, row)
        for table, rows in tables
        if _ID_COLUMN in table.columns
        for row in rows
    }


# TODO: Validate
def _sort_key(row: Mapping[str, Any]) -> str:
    """Return what a row is ordered by.

    Every list in the dump is ordered this way rather than left in the order the
    database handed it over, because that order is the database's to change and a
    run that read the same rows in another order would read as a run that found
    different ones.
    """
    return json.dumps(row, sort_keys=True, default=str)


# TODO: Validate
def database_json(session: Session) -> str:
    """Return the whole database, bar the excluded tables, as its stored text."""
    tables = _read_tables(session)
    rows_by_id = _rows_by_id(tables)
    keys: KeyById = {}
    dump: TableRows = {
        table.name: sorted(
            (
                {
                    name: _dump_value(value, rows_by_id, keys)
                    for name, value in row.items()
                }
                for row in rows
            ),
            key=_sort_key,
        )
        for table, rows in tables
        if table.name not in EXCLUDED_TABLES
    }
    return json.dumps(dump, indent=2)


# TODO: Validate
def state_diff(expected: str, actual: str) -> str:
    """Return what changed between the recorded dump and the one a run produced."""
    return "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile="recorded",
            tofile="actual",
            lineterm="",
        ),
    )
