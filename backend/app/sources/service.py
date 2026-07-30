# TODO: Validate
"""Source service functions."""

from sqlmodel import Session, col, func, select

from app.plugins.models import Plugin
from app.sources.models import Source
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User

OTHER_SOURCE_KEY = "Other"


def sources_by_key(session: Session) -> dict[str, Source]:
    """Return the installed plugins' stored `Source`s, keyed by source key.

    Only sources owned by the plugin user count as installed sources; a source
    imported under a user's own plugin is private to them and is left out. A
    plugin that splits its media across several sources (e.g. Amazon Prime
    Video's channels) is represented by each of those sources.
    """
    sources = session.exec(
        select(Source)
        .join(Plugin, col(Source.plugin_id) == Plugin.id)
        .join(User, col(Plugin.user_id) == User.id)
        .where(
            col(Source.deleted_at).is_(None),
            func.lower(User.email) == PLUGIN_USER_EMAIL,
        )
        .order_by(col(Source.name), col(Source.key)),
    ).all()
    return {source.key: source for source in sources}


def source_keys(session: Session) -> list[str]:
    """Return the key of every installed plugin's `Source`, ordered for display."""
    return list(sources_by_key(session))
