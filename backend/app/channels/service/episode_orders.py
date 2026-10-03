# TODO: Validate
import uuid

from fastapi import HTTPException
from sqlmodel import Session, col, select

from app.channels.models import ChannelTitle
from app.channels.schemas import (
    ChannelEpisodeOrderInput,
    ChannelEpisodeOrderOption,
    ChannelEpisodeOrderOutput,
)
from app.tmdb_media.models import TmdbEpisodeOrder


# TODO: Validate
def _orders_of(session: Session, channel_title: ChannelTitle) -> list[TmdbEpisodeOrder]:
    return list(
        session.exec(
            select(TmdbEpisodeOrder)
            .where(col(TmdbEpisodeOrder.tmdb_title_id) == channel_title.tmdb_title_id)
            .order_by(col(TmdbEpisodeOrder.type), col(TmdbEpisodeOrder.name)),
        ).all(),
    )


# TODO: Validate
def _output(
    session: Session,
    channel_title: ChannelTitle,
) -> ChannelEpisodeOrderOutput:
    return ChannelEpisodeOrderOutput(
        tmdb_episode_order_id=channel_title.tmdb_episode_order_id,
        orders=[
            ChannelEpisodeOrderOption(
                id=order.id,
                tmdb_group_id=order.tmdb_group_id,
                name=order.name,
                description=order.description,
                group_count=order.group_count,
                episode_count=order.episode_count,
                type=order.type,
            )
            for order in _orders_of(session, channel_title)
        ],
    )


# TODO: Validate
def channel_episode_order_output(
    session: Session,
    channel_title: ChannelTitle,
) -> ChannelEpisodeOrderOutput:
    return _output(session, channel_title)


# TODO: Validate
def update_channel_episode_order(
    session: Session,
    order_input: ChannelEpisodeOrderInput,
    channel_title: ChannelTitle,
) -> ChannelEpisodeOrderOutput:
    order_id: uuid.UUID | None = order_input.tmdb_episode_order_id
    if order_id is not None and not any(
        order.id == order_id for order in _orders_of(session, channel_title)
    ):
        message = "That episode order is not one TMDB publishes for this title."
        raise HTTPException(status_code=422, detail=message)
    channel_title.tmdb_episode_order_id = order_id
    session.add(channel_title)
    session.commit()
    session.refresh(channel_title)
    return _output(session, channel_title)
