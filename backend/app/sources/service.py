# TODO: Validate
"""Source service functions."""

import uuid

from sqlmodel import Session, col, func, select

from app.episodes.models import Episode
from app.plugins.identifiers import (
    CUSTOM_MEDIA_FAVICON_URL,
    CUSTOM_MEDIA_NAME,
    CUSTOM_MEDIA_PLUGIN_KEY,
    CUSTOM_MEDIA_SOURCE_KEY,
)
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

OTHER_SOURCE_KEY = "Other"


# TODO: Validate
def sources_by_key(session: Session) -> dict[str, Source]:
    """Return the installed plugins' stored `Source`s, keyed by source key.

    A plugin that splits its media across several sources (e.g. Amazon Prime
    Video's channels) is represented by each of those sources.
    """
    sources = session.exec(
        select(Source)
        .join(Plugin, col(Source.plugin_id) == Plugin.id)
        .where(col(Source.deleted_at).is_(None))
        .order_by(col(Source.name), col(Source.key)),
    ).all()
    return {source.key: source for source in sources}


# TODO: Validate
def episode_counts_by_source_id(session: Session) -> dict[uuid.UUID, int]:
    """Return the number of live episodes each `Source` provides, keyed by source id."""
    # Every row belongs to the source that wrote it, whether it is the record of the
    # media or a non-canonical row of one, so both are counted under it.
    rows = session.exec(
        select(Source.id, func.count(col(Episode.id)))
        .select_from(Show)
        .join(Source, col(Show.source_id) == Source.id)
        .join(Season, col(Season.show_id) == Show.id)
        .join(Episode, col(Episode.season_id) == Season.id)
        .where(
            col(Show.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Source.id)),
    ).all()
    return dict(rows)


# TODO: Validate
def source_keys(session: Session) -> list[str]:
    """Return the key of every installed plugin's `Source`, ordered for display."""
    return list(sources_by_key(session))


# TODO: Validate
def get_or_create_custom_media_source(session: Session) -> Source:
    plugin = Plugin.get(session, CUSTOM_MEDIA_PLUGIN_KEY)
    if plugin is None:
        plugin = Plugin(key=CUSTOM_MEDIA_PLUGIN_KEY, name=CUSTOM_MEDIA_NAME)
        session.add(plugin)
        session.commit()
        session.refresh(plugin)

    source = Source.get(session, plugin, CUSTOM_MEDIA_SOURCE_KEY)
    if source is None:
        source = Source(
            key=CUSTOM_MEDIA_SOURCE_KEY,
            name=CUSTOM_MEDIA_NAME,
            favicon_url=CUSTOM_MEDIA_FAVICON_URL,
            plugin_id=plugin.id,
        )
        session.add(source)
        session.commit()
        session.refresh(source)
    elif source.favicon_url != CUSTOM_MEDIA_FAVICON_URL:
        source.favicon_url = CUSTOM_MEDIA_FAVICON_URL
        session.commit()
        session.refresh(source)
    return source
