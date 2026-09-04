# TODO: Validate


import uuid
from collections.abc import Collection, Sequence
from functools import cache
from uuid import UUID

from sqlmodel import Session, col, delete, select

from app.channels.models import (
    Channel,
    ChannelSavedEpisodeOrder,
)
from app.channels.schemas import (
    ChannelOptions,
    ChannelOrderInput,
    SortKeyInput,
    SortOptionOutput,
    WhitelistEpisodeOutput,
)
from app.channels.service.episodes import _canonical_episode_id, _SeasonEpisodeRow
from app.episodes.models import Episode
from app.models import ZERO_LAST_SUFFIX
from app.seasons.models import Season


# TODO: Validate
def set_channel_order(
    session: Session,
    channel: Channel,
    episode_ids: Sequence[UUID],
) -> None:
    """Save the order `episode_ids` are in, as an order of episodes themselves.

    The ids each name one website's row, which is what the channel was read as,
    but what is saved is an order of the episodes: the same episode arriving from
    another website next time takes the position already held for it. A row that
    is not yet of anything has no position to be given one.
    """
    session.exec(  # type: ignore[call-overload]
        delete(ChannelSavedEpisodeOrder).where(
            col(ChannelSavedEpisodeOrder.channel_id) == channel.id,
        ),
    )
    session.flush()
    seen: set[UUID] = set()
    position = 0
    for episode_id in episode_ids:
        canonical_episode_id = _canonical_episode_id(session, episode_id)
        if canonical_episode_id is None or canonical_episode_id in seen:
            continue
        seen.add(canonical_episode_id)
        session.add(
            ChannelSavedEpisodeOrder(
                channel_id=channel.id,
                canonical_episode_id=canonical_episode_id,
                position=position,
            ),
        )
        position += 1
    session.commit()


# TODO: Validate
def _sort_option_label(model_name: str, field_name: str) -> str:
    """Name a sortable field as it reads in the sort picker."""
    base_field = field_name.removesuffix(ZERO_LAST_SUFFIX)
    variant = " (0 Last)" if base_field != field_name else ""
    return f"{model_name} - {base_field.replace('_', ' ').title()}{variant}"


# TODO: Validate
@cache
def get_sort_options() -> list[SortOptionOutput]:
    """Build and cache the list of all possible sorting options."""
    options: list[SortOptionOutput] = [
        SortOptionOutput(
            label=_sort_option_label(model_name.title(), field_name),
            # If this value does not match it should raise an error.
            model=model_name,  # type: ignore[arg-type]
            field=field_name,
        )
        for model_name, model in SortKeyInput.MODEL_MAP.items()
        for field_name in model.SORTABLE_FIELDS
    ]
    options.sort(key=lambda option: option.label)
    return options


# An episode the website never ordered sits after every episode it did.
_UNORDERED = float("inf")


# TODO: Validate
def _canonical_orders(
    session: Session,
    canonical_episode_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, float]:
    """Read where each canonical episode sits, keyed by its id.

    A row is listed under the number the episode itself carries rather than the number
    the website gave its non-canonical row, so it is ordered on that same number. Two
    websites number an episode differently, and one of them numbering a recap or a
    double-length episode its own way is what puts a non-canonical row's own order out
    of step with the episode being listed.
    """
    if not canonical_episode_ids:
        return {}
    rows = session.exec(
        select(Episode.id, Episode.episode_number, Episode.sort_order).where(
            col(Episode.id).in_(set(canonical_episode_ids)),
        ),
    ).all()
    orders: dict[uuid.UUID, float] = {}
    for episode_id, episode_number, sort_order in rows:
        order = episode_number if episode_number is not None else sort_order
        if order is not None:
            orders[episode_id] = float(order)
    return orders


# TODO: Validate
def _episode_sort_key(
    episode: Episode | WhitelistEpisodeOutput | _SeasonEpisodeRow,
    order: float | None = None,
) -> tuple[float, str]:
    """Order an episode by where the episode sits, then by its own identifier.

    `order` is where the canonical row puts it, which is what the row is labelled
    with; where there is none, the website's own order stands in. A row nothing
    ordered sits after the ones something did, and the identifier settles the
    rest, so a page boundary falls in the same place on every request rather than
    wherever the database happened to answer in.
    """
    if order is None:
        order = _UNORDERED if episode.sort_order is None else float(episode.sort_order)
    return order, str(episode.id)


# TODO: Validate
def _season_sort_key(season: Season) -> tuple[bool, int, str]:
    number = (
        season.season_number if season.season_number is not None else season.sort_order
    )
    return number is None, number or 0, str(season.id)


# TODO: Validate
def set_default_order(
    session: Session,
    channel: Channel,
    channel_options: ChannelOptions,
) -> Channel:
    """Update the default sort order for a `Channel`."""
    exclude: set[str] = set()
    if "random_seed" not in channel_options.model_fields_set:
        exclude.add("random_seed")
    channel.default_order = channel_options.model_dump_json(
        by_alias=True,
        exclude_defaults=True,
        exclude_unset=False,
        exclude=exclude,
    )
    session.commit()
    session.refresh(channel)
    return channel


# TODO: Validate
def set_custom_order(
    session: Session,
    channel: Channel,
    order_input: ChannelOrderInput,
) -> Channel:
    """Set the custom episode order for a `Channel`."""
    set_channel_order(session, channel, order_input.episode_ids)
    session.refresh(channel)
    return channel
