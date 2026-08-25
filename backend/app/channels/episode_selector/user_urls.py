# TODO: Validate
import uuid
from collections.abc import Sequence
from typing import Any

from sqlmodel import Session

from app.channels.episode_selector.source_dedup import SourceDedupConfig
from app.channels.schemas import ChannelOptions
from app.episodes.user_urls import user_episode_urls
from app.plugins.identifiers import CUSTOM_MEDIA_SOURCE_KEY
from app.sources.models import Source
from app.sources.service import get_or_create_custom_media_source
from app.users.models import User


# TODO: Validate
def _channel_allows(channel_options: ChannelOptions, source_id: uuid.UUID) -> bool:
    if not channel_options.source_ids:
        return True
    if channel_options.source_ids_is_blacklist:
        return source_id not in channel_options.source_ids
    return source_id in channel_options.source_ids


# TODO: Validate
def apply_user_episode_urls(  # noqa: PLR0913 - Every part of the ranking is a separate input.
    session: Session,
    user: User | None,
    rows: Sequence[Any],
    source_keys: dict[uuid.UUID, str],
    source_config: SourceDedupConfig,
    channel_options: ChannelOptions,
) -> Source | None:
    if user is None or CUSTOM_MEDIA_SOURCE_KEY in source_config.disabled_keys:
        return None
    custom_source = get_or_create_custom_media_source(session)
    if not _channel_allows(channel_options, custom_source.id):
        return None

    stored = user_episode_urls(
        session,
        user,
        [
            row.canonical_episode_id
            for row in rows
            if row.canonical_episode_id is not None
        ],
    )
    if not stored:
        return None

    custom_priority = source_config.priority_for(CUSTOM_MEDIA_SOURCE_KEY)
    used = False
    for row in rows:
        url = stored.get(row.canonical_episode_id)
        if url is None:
            continue
        if custom_priority <= source_config.priority_for(source_keys.get(row.id)):
            row.url = url
            row.source_id = custom_source.id
            used = True
    return custom_source if used else None
