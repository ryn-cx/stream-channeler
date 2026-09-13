# TODO: Validate


import uuid
from collections.abc import Collection
from random import shuffle
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, col, delete, func, select

from app.channels.models import (
    Channel,
    ChannelFavorite,
    ChannelQueue,
    ChannelSavedEpisodeOrder,
    ChannelTitle,
)
from app.channels.schemas import (
    AutomaticChannelUserOutput,
    ChannelAdminCreate,
    ChannelAdminUpdate,
    ChannelCreate,
    ChannelListOutput,
    ChannelOutput,
    ChannelPublicListOutput,
    ChannelsPublic,
)
from app.models import Visibility
from app.schemas import Message, RecordScope, ScopedReadOptions
from app.service.responses import scoped_list_response
from app.users.models import User
from app.users.plugin_user import is_plugin_user


# TODO: Validate
def create_channel(
    session: Session,
    user: User,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by `user`."""
    channel = Channel.model_validate(channel_in, update={"user_id": user.id})
    session.add(channel)
    session.commit()
    return channel


# TODO: Validate
def admin_create_channel(
    session: Session,
    channel_in: ChannelAdminCreate,
) -> Channel:
    """Create a `Channel` for the `User` the admin named, with its `score`.

    The owner comes from the request rather than from whoever is signed in, which
    is what lets an admin set a `Channel` up on someone else's behalf.
    """
    owner = session.get(User, channel_in.user_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="User not found")
    channel = Channel.model_validate(channel_in)
    session.add(channel)
    session.commit()
    return channel


# TODO: Validate
def admin_update_channel(
    session: Session,
    channel: Channel,
    channel_in: ChannelAdminUpdate,
) -> Channel:
    """Update any field on `channel` as an admin, including who owns it."""
    updates = channel_in.model_dump(exclude_unset=True)
    # A `Channel` always belongs to someone, so an unset owner leaves the one it
    # already has rather than clearing it.
    if updates.get("user_id") is None:
        updates.pop("user_id", None)
    elif session.get(User, updates["user_id"]) is None:
        raise HTTPException(status_code=404, detail="User not found")
    channel.sqlmodel_update(updates)
    session.commit()
    session.refresh(channel)
    return channel


# TODO: Validate
def viewer_is_privileged(channel: Channel, viewer: User | None) -> bool:
    """Return whether `viewer` may see `channel`'s owner and `score`."""
    return bool(viewer and (viewer.is_superuser or viewer.id == channel.user_id))


# TODO: Validate
def channel_output(channel: Channel, viewer: User | None) -> ChannelOutput:
    output = ChannelOutput.model_validate(channel)
    output.username = channel.user.username
    if not channel.anonymous:
        return output
    if viewer_is_privileged(channel, viewer):
        return output
    output.user_id = None
    output.username = None
    return output


# TODO: Validate
def channel_favorite_counts(
    session: Session,
    channel_ids: Collection[UUID],
) -> dict[UUID, int]:
    if not channel_ids:
        return {}
    rows = session.exec(
        select(ChannelFavorite.channel_id, func.count())
        .where(col(ChannelFavorite.channel_id).in_(channel_ids))
        .group_by(col(ChannelFavorite.channel_id)),
    ).all()
    return dict(rows)


# TODO: Validate
def scoped_channel_list_output(
    session: Session,
    viewer: User | None,
    read_options: ScopedReadOptions,
) -> ChannelsPublic:
    """List `Channel`s for the requested scope."""
    response = scoped_list_response(
        session=session,
        model=Channel,
        viewer=viewer,
        read_options=read_options,
        schema=ChannelListOutput,
        response_model=ChannelsPublic,
        favorite_model=ChannelFavorite,
        favorite_record_id=ChannelFavorite.channel_id,
        # On the public list, equally scored channels are shuffled rather than shown
        # in a fixed order so no channel is permanently ranked above its peers.
        random_tiebreaker=read_options.scope == RecordScope.public,
        rank_by_favorites=True,
    )
    favorite_counts = channel_favorite_counts(
        session,
        [row.id for row in response.data],
    )
    for row in response.data:
        row.favorite_count = favorite_counts.get(row.id, 0)
    # In the `favorites` scope, overlay each row with the viewer's private
    # customization so their own name/number are what get displayed.
    if read_options.scope == RecordScope.favorites and viewer is not None:
        channel_ids = [row.id for row in response.data]
        if channel_ids:
            favorites = session.exec(
                select(ChannelFavorite).where(
                    ChannelFavorite.user_id == viewer.id,
                    col(ChannelFavorite.channel_id).in_(channel_ids),
                ),
            ).all()
            customization_by_channel = {
                favorite.channel_id: favorite for favorite in favorites
            }
            for row in response.data:
                favorite = customization_by_channel.get(row.id)
                if favorite is not None:
                    row.custom_name = favorite.name
                    row.custom_channel_number = favorite.channel_number
    return response


# TODO: Validate
def public_channel_output(
    channel: Channel,
    username: str | None,
    favorite_count: int,
) -> ChannelListOutput:
    anonymous = channel.anonymous
    return ChannelListOutput(
        id=channel.id,
        user_id=None if anonymous else channel.user_id,
        name=channel.name,
        channel_number=channel.channel_number,
        visibility=channel.visibility,
        default_order=channel.default_order,
        description=channel.description,
        anonymous=anonymous,
        username=None if anonymous else username,
        score=channel.score,
        favorite_count=favorite_count,
    )


# TODO: Validate
def public_channels_of_user(
    session: Session,
    user_id: uuid.UUID,
) -> ChannelPublicListOutput:
    """List a `User`'s public, non-anonymous `Channel`s, highest score first."""
    rows = session.exec(
        select(Channel, User.username)
        .join(User, col(User.id) == Channel.user_id)
        .where(
            Channel.user_id == user_id,
            Channel.visibility == Visibility.public,
            col(Channel.anonymous).is_(False),
        ),
    ).all()
    favorite_counts = channel_favorite_counts(
        session,
        [channel.id for channel, _username in rows],
    )
    data = [
        public_channel_output(
            channel,
            username,
            favorite_counts.get(channel.id, 0),
        )
        for channel, username in rows
    ]
    shuffle(data)
    data.sort(
        key=lambda channel: (channel.favorite_count, channel.score),
        reverse=True,
    )
    return ChannelPublicListOutput(data=data, count=len(data))


# TODO: Validate
def channels_of_user(session: Session, user_id: uuid.UUID) -> list[ChannelListOutput]:
    """List every `Channel` a single `User` may edit."""
    rows = session.exec(
        select(Channel, User.username)
        .join(User, col(User.id) == Channel.user_id)
        .where(Channel.user_id == user_id),
    ).all()
    favorite_counts = channel_favorite_counts(
        session,
        [channel.id for channel, _username in rows],
    )
    return [
        ChannelListOutput.model_validate(
            channel,
            update={
                "username": username,
                "favorite_count": favorite_counts.get(channel.id, 0),
            },
        )
        for channel, username in rows
    ]


# TODO: Validate
def admin_update_channel_output(
    session: Session,
    channel: Channel,
    channel_in: ChannelAdminUpdate,
) -> ChannelListOutput:
    """Update any field on any `Channel` as an admin, including `score`."""
    channel = admin_update_channel(session, channel, channel_in)
    username = session.get_one(User, channel.user_id).username
    favorite_counts = channel_favorite_counts(session, [channel.id])
    return ChannelListOutput.model_validate(
        channel,
        update={
            "username": username,
            "favorite_count": favorite_counts.get(channel.id, 0),
        },
    )


# TODO: Validate
def automatic_channel_users(session: Session) -> list[AutomaticChannelUserOutput]:
    rows = session.exec(
        select(User, func.count(col(Channel.id)))
        .join(Channel, col(Channel.user_id) == col(User.id))
        .where(is_plugin_user(User.email), col(User.is_superuser).is_(False))
        .group_by(col(User.id))
        .order_by(col(User.email)),
    ).all()
    return [
        AutomaticChannelUserOutput(
            id=user.id,
            username=user.username,
            email=user.email,
            channel_count=channel_count,
        )
        for user, channel_count in rows
    ]


# TODO: Validate
def _automatic_channel_user(session: Session, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if "@" in user.email or user.is_superuser:
        raise HTTPException(
            status_code=400,
            detail=f"{user.email} is not an automatic channel user.",
        )
    return user


# TODO: Validate
def clear_automatic_channels(session: Session, user_id: uuid.UUID) -> Message:
    """Empty every `Channel` an automatic channel `User` owns.

    The channels themselves are kept, so what a viewer subscribed to or combined
    is still there to be filled in again. A source writes its channels from the
    queue, so the queued URLs go with the titles: a URL left behind as already
    imported would never be imported into the emptied channel again.
    """
    user = _automatic_channel_user(session, user_id)
    channel_ids = session.exec(
        select(Channel.id).where(Channel.user_id == user.id),
    ).all()
    if channel_ids:
        for model in (ChannelTitle, ChannelQueue, ChannelSavedEpisodeOrder):
            session.exec(  # type: ignore[call-overload]
                delete(model).where(col(model.channel_id).in_(channel_ids)),
            )
        session.commit()
    return Message(
        message=f"Emptied {len(channel_ids)} channels owned by {user.email}",
    )
