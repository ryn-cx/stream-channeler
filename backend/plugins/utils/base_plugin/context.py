# TODO: Validate
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect as sa_inspect

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin
    from app.sources.models import Source

_CONTEXTS_KEY = "base_plugin_contexts"


# TODO: Validate
@dataclass
class PluginContext:
    plugin: Plugin
    sources: dict[str, Source] = field(default_factory=dict)
    canonical_source: Source | None = None
    reusable_files: dict[object, Any] = field(default_factory=dict)


# TODO: Validate
def _contexts(session: Session) -> dict[str, PluginContext]:
    contexts: dict[str, PluginContext] = session.info.setdefault(_CONTEXTS_KEY, {})
    return contexts


# TODO: Validate
def _is_live(record: object, session: Session) -> bool:
    state = sa_inspect(record, raiseerr=False)
    if state is None or state.session is not session or state.deleted:
        return False
    return bool(state.persistent or state.pending)


# TODO: Validate
def _context_is_live(context: PluginContext, session: Session) -> bool:
    records: list[object] = [context.plugin, *context.sources.values()]
    if context.canonical_source is not None:
        records.append(context.canonical_source)
    return all(_is_live(record, session) for record in records)


# TODO: Validate
def plugin_context(session: Session, plugin_key: str) -> PluginContext | None:
    context = _contexts(session).get(plugin_key)
    if context is None:
        return None
    if not _context_is_live(context, session):
        del _contexts(session)[plugin_key]
        return None
    return context


# TODO: Validate
def store_plugin_context(
    session: Session,
    plugin_key: str,
    context: PluginContext,
) -> None:
    _contexts(session)[plugin_key] = context
