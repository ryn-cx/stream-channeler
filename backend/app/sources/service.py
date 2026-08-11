# TODO: Validate
"""Source service functions."""

import uuid

from sqlmodel import Session, col, func, select

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User

OTHER_SOURCE_KEY = "Other"


# TODO: Validate
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


# TODO: Validate
def episode_counts_by_source_id(session: Session) -> dict[uuid.UUID, int]:
    """Return the number of live episodes each `Source` provides, keyed by source id."""
    rows = session.exec(
        select(Show.source_id, func.count(col(Episode.id)))
        .join(Season, col(Season.show_id) == Show.id)
        .join(Episode, col(Episode.season_id) == Season.id)
        .where(
            col(Show.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Show.source_id)),
    ).all()
    return dict(rows)


# TODO: Validate
def source_keys(session: Session) -> list[str]:
    """Return the key of every installed plugin's `Source`, ordered for display."""
    return list(sources_by_key(session))
