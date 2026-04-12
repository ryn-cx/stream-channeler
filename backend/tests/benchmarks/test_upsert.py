# TODO: Validate
"""Benchmark: original upsert vs Session.merge-based upsert.

Creates and updates 1,000 plugins with each approach and asserts the
original implementation is faster.
"""

import time
from collections.abc import Callable

from sqlmodel import Session, select

from app.plugins.models import Plugin
from app.users.models import User
from app.utils import tz_datetime
from tests.conftest import init_db, reset_tables, test_engine

COUNT = 1_000


def _create_user(session: Session) -> User:
    user = User(
        email="bench@example.com",
        hashed_password="fake",
        full_name="Benchmark User",
    )
    session.add(user)
    session.flush()
    return user


def _merge_upsert(
    plugin: Plugin,
    session: Session,
    user: User,
) -> Plugin:
    """Alternative upsert using Session.merge."""
    dumped = plugin.model_dump(exclude={"update_at"})

    existing = Plugin.get_from_memory(session, user, plugin.key)
    if existing:
        dumped["id"] = existing.id
        dumped["created_at"] = existing.created_at

    instance = Plugin.model_validate(dumped)
    with session.no_autoflush:
        merged: Plugin = session.merge(instance)
    merged.set_update_at(plugin.update_at)

    if not existing:
        user.plugins.append(merged)

    return merged


def _run_original_upsert(session: Session, user: User) -> None:
    timestamp = tz_datetime.now()

    for index in range(COUNT):
        Plugin(
            key=f"plugin_{index}",
            public=True,
            data_timestamp=timestamp,
            user_id=user.id,
        ).upsert(user, None)
    session.flush()

    plugins = session.exec(
        select(Plugin).where(Plugin.user_id == user.id),
    ).all()
    for plugin in plugins:
        Plugin(
            key=plugin.key,
            public=True,
            name=f"Updated {plugin.key}",
            data_timestamp=timestamp,
            user_id=user.id,
        ).upsert(user, plugin)
    session.flush()


def _run_merge_upsert(session: Session, user: User) -> None:
    timestamp = tz_datetime.now()

    for index in range(COUNT):
        _merge_upsert(
            Plugin(
                key=f"plugin_{index}",
                public=True,
                data_timestamp=timestamp,
                user_id=user.id,
            ),
            session,
            user,
        )
    session.flush()
    _cache = user.plugins

    for index in range(COUNT):
        _merge_upsert(
            Plugin(
                key=f"plugin_{index}",
                public=True,
                name=f"Updated plugin_{index}",
                data_timestamp=timestamp,
                user_id=user.id,
            ),
            session,
            user,
        )
    session.flush()


def _time_benchmark(function: Callable[[Session, User], None]) -> float:
    reset_tables(test_engine)
    with Session(test_engine) as session:
        init_db(session)
        user = _create_user(session)
        session.flush()

        start = time.perf_counter()
        function(session, user)
        session.flush()
        elapsed = time.perf_counter() - start

        plugin_count = len(
            session.exec(
                select(Plugin).where(Plugin.user_id == user.id),
            ).all(),
        )
        assert plugin_count == COUNT
        session.rollback()

    return elapsed


def test_original_upsert_is_faster_than_merge() -> None:
    original_time = _time_benchmark(_run_original_upsert)
    merge_time = _time_benchmark(_run_merge_upsert)

    assert original_time < merge_time, (
        f"Original upsert ({original_time:.3f}s) should be faster "
        f"than merge upsert ({merge_time:.3f}s)"
    )
