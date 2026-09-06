# TODO: Validate


import uuid

from sqlmodel import Session

from app.channels.models import (
    Channel,
)
from app.channels.service.titles import titles_by_canonical_id
from app.sources.schemas import SourcePublic
from app.sources.service.lookup import get_or_create_custom_media_source


# TODO: Validate
def channel_sources_output(
    channel: Channel,
    session: Session,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    non_canonical_titles = titles_by_canonical_id(
        session,
        {channel_title.canonical_title_id for channel_title in channel.titles},
    )
    for channel_title in channel.titles:
        for title in non_canonical_titles[channel_title.canonical_title_id]:
            source = title.source
            if source.id not in sources:
                sources[source.id] = SourcePublic.model_validate(source)

    custom_source = get_or_create_custom_media_source(session)
    sources.setdefault(
        custom_source.id,
        SourcePublic.model_validate(custom_source),
    )

    return list(sources.values())
