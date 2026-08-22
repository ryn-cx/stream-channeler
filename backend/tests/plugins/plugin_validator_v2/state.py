# TODO: Validate
"""The whole database written down as the two runs of a test compare it."""

import difflib
import json
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from typing import Any

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

type MediaRecord = Plugin | Source | Show | Season | Episode
type CanonicalRecord = Show | Season | Episode
type Record = MediaRecord | CanonicalRecord
type KeyById = dict[uuid.UUID, str]

CHILDREN: dict[type, str] = {
    Plugin: "sources",
    Source: "shows",
    Show: "seasons",
    Season: "episodes",
}

_ID_FIELD = "id"
_ID_SUFFIX = "_id"


# TODO: Validate
def _children(record: Record) -> list[Any]:
    """Return the children of `record` that are worth writing down.

    A plugin gives every provider it tracks a source whether or not anything was
    imported from it, and an empty one says nothing two runs can compare.
    """
    child_name = CHILDREN.get(type(record))
    if child_name is None:
        return []
    child_records: list[Any] = getattr(record, child_name)
    if isinstance(record, Plugin):
        return [source for source in child_records if source.shows]
    return child_records


# TODO: Validate
def _dump_value(value: object) -> object:
    """Return `value` as something JSON holds and two runs write the same way."""
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return value


# TODO: Validate
def key_by_id(
    plugins: Sequence[Plugin],
    canonical_shows: Sequence[Show],
    users: Sequence[User],
) -> KeyById:
    """Return the key of every record an id in the dump can name.

    An id is generated afresh on every run, so an id written down as it is says
    nothing that two runs can compare. Every record has a key that says the same
    thing and stays put, so what an id names is written as that record's key,
    which leaves an id pointing at the wrong record readable as the wrong name
    rather than as one meaningless value against another.
    """
    # A user has no key, and the only one a plugin's records belong to is the
    # one every plugin runs as, so its address is what stands in for one.
    keys: KeyById = {user.id: user.email for user in users}
    for plugin in plugins:
        keys[plugin.id] = plugin.key
        for source in plugin.sources:
            keys[source.id] = source.key
            for show in source.shows:
                keys[show.id] = show.key
                for season in show.seasons:
                    keys[season.id] = season.key
                    for episode in season.episodes:
                        keys[episode.id] = episode.key
    for canonical_show in canonical_shows:
        keys[canonical_show.id] = canonical_show.key
        for canonical_season in canonical_show.seasons:
            keys[canonical_season.id] = canonical_season.key
            for canonical_episode in canonical_season.episodes:
                keys[canonical_episode.id] = canonical_episode.key
    return keys


# TODO: Validate
def _dump_id(record: Record, field_name: str, value: object, keys: KeyById) -> object:
    """Return the key of the record `value` names."""
    if value is None:
        return None
    if not isinstance(value, uuid.UUID) or value not in keys:
        msg = (
            f"{type(record).__name__}.{field_name} names nothing that was read: {value}"
        )
        raise KeyError(msg)
    return keys[value]


# TODO: Validate
def dump_record(record: Record, keys: KeyById) -> dict[str, Any]:
    """Dump a record and its children, every id written as the key it names."""
    data = {
        name: (
            _dump_id(record, name, value, keys)
            if name == _ID_FIELD or name.endswith(_ID_SUFFIX)
            else _dump_value(value)
        )
        for name, value in record.model_dump().items()
    }
    if isinstance(record, Show):
        data["canonical_show_keys"] = _canonical_show_keys(record)
    if child_name := CHILDREN.get(type(record)):
        data[child_name] = _by_key(
            dump_record(child, keys) for child in _children(record)
        )
    return data


# TODO: Validate
def _by_key(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the records in the order their keys put them in.

    Every list in the export is ordered this way rather than left in the order
    the database handed it over, because that order is the database's to change
    and a run that read the same records in another order would read as a run
    that found different ones.
    """
    return sorted(records, key=lambda record: record["key"])


# TODO: Validate
def _canonical_show_keys(show: Show) -> list[str]:
    """Return the key of every title `show` is a copy of.

    A website that files two titles under one listing - a channel whose uploads
    are two series, a service that sells a sequel as another season - is a copy
    of each of them and no more a copy of one than of another, so they are dumped
    as a set with nothing leading it.
    """
    return sorted({link.canonical_show.key for link in show.canonical_show_links})


# TODO: Validate
def state_json(
    plugins: Sequence[Plugin],
    canonical_shows: Sequence[Show],
    users: Sequence[User],
) -> str:
    """Return everything a test compares, as the text it is stored as."""
    keys = key_by_id(plugins, canonical_shows, users)
    state = {
        "plugins": _by_key(dump_record(plugin, keys) for plugin in plugins),
        "canonical_shows": _by_key(
            dump_record(canonical_show, keys) for canonical_show in canonical_shows
        ),
    }
    return json.dumps(state, indent=2)


# TODO: Validate
def state_diff(expected: str, actual: str) -> str:
    """Return what changed between the recorded state and the one a run produced."""
    return "\n".join(
        difflib.unified_diff(
            expected.splitlines(),
            actual.splitlines(),
            fromfile="recorded",
            tofile="actual",
            lineterm="",
        ),
    )
