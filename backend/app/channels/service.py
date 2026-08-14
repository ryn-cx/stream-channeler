# TODO: Validate
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from datetime import datetime
from functools import cache
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, delete, select

from app.canonical_media.filters import canonical_id_column, is_canonical, is_copy
from app.channels.models import (
    Channel,
    ChannelCombinedChannel,
    ChannelEpisodeFilter,
    ChannelFavorite,
    ChannelQueue,
    ChannelSavedEpisodeOrder,
    ChannelSeasonFilter,
    ChannelShow,
    ChannelSourceFilter,
    URLStatus,
)
from app.channels.schemas import (
    ChannelAdminCreate,
    ChannelAdminUpdate,
    ChannelCreate,
    ChannelListOutput,
    ChannelOutput,
    ChannelsPublic,
    CombinedChannelInput,
    SortKeyInput,
    SortOptionOutput,
    WhitelistShowInput,
)
from app.episodes.models import Episode
from app.media.identifiers import TMDB_PLUGIN_KEY
from app.models import ZERO_LAST_SUFFIX
from app.plugins.models import Plugin
from app.schemas import RecordScope, ScopedReadOptions
from app.seasons.models import Season
from app.service import scoped_list_response
from app.shows.models import Show, ShowCanonicalShow
from app.sources.models import Source
from app.users.models import User


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
def shows_by_canonical_id(
    session: Session,
    canonical_show_ids: Collection[UUID],
) -> dict[UUID, list[Show]]:
    """Return every website's copy of each title in `canonical_show_ids`.

    A `ChannelShow` names a title rather than one website's copy of it, so the
    copies it stands for have to be looked up by the title they are all of. What
    makes a copy one of them is carrying one of the title's episodes: a listing
    that mixes titles is linked to each of them, but it is only a place to watch
    the ones it has episodes of, so a series page linked to the film it spun off
    is not somewhere that film can be watched. A copy nobody has imported the
    episodes of yet has only its own word for the title it is of, so the copies
    naming the title as the one they are chiefly of are counted as well.

    A copy also carries episodes nothing was minted for them to be copies of,
    because the title had no record of them to match them against. They are the
    episodes themselves, and the only word on what title they belong to is the
    link their listing carries, so a copy is one of the title's places on the
    strength of those as well.
    """
    grouped: dict[UUID, list[Show]] = defaultdict(list)
    if not canonical_show_ids:
        return grouped

    listed: dict[UUID, set[UUID]] = defaultdict(set)

    # TODO: Validate
    def add(canonical_show_id: UUID, show: Show) -> None:
        if show.id in listed[canonical_show_id]:
            return
        listed[canonical_show_id].add(show.id)
        grouped[canonical_show_id].append(show)

    copy_season = aliased(Season)
    canonical_episode = aliased(Episode)
    canonical_season = aliased(Season)
    carried = session.exec(
        select(canonical_season.show_id, Show)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(
            canonical_episode,
            col(canonical_episode.id) == col(Episode.canonical_episode_id),
        )
        .join(
            canonical_season,
            col(canonical_season.id) == col(canonical_episode.season_id),
        )
        .join(copy_season, col(copy_season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(copy_season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(canonical_season.show_id).in_(canonical_show_ids),
            col(Episode.deleted_at).is_(None),
            col(copy_season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
            # TMDB only supplies the metadata other websites left out, so its copy of
            # a title is never one of the websites the title can be watched on.
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .distinct(),
    ).all()
    for canonical_show_id, show in carried:
        add(canonical_show_id, show)

    linked_season = aliased(Season)
    linked = session.exec(
        select(ShowCanonicalShow.canonical_show_id, Show)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(linked_season, col(linked_season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(linked_season.show_id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Show.id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(ShowCanonicalShow.canonical_show_id).in_(canonical_show_ids),
            is_canonical(Episode),
            is_copy(Show),
            col(Episode.deleted_at).is_(None),
            col(linked_season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .distinct(),
    ).all()
    for canonical_show_id, show in linked:
        add(canonical_show_id, show)

    chiefly = session.exec(
        select(Show.canonical_show_id, Show)  # type: ignore[call-overload]
        .select_from(Show)
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Show.canonical_show_id).in_(canonical_show_ids),
            col(Show.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        ),
    ).all()
    for canonical_show_id, show in chiefly:
        add(canonical_show_id, show)

    return grouped


# TODO: Validate
def tmdb_shows_by_canonical_id(
    session: Session,
    canonical_show_ids: Iterable[UUID],
) -> dict[UUID, list[Show]]:
    """Return TMDB's own copy of each title, keyed by the title it is of.

    TMDB is not one of the websites a title can be watched on, so its copies are
    gathered apart from theirs rather than alongside them.

    A title TMDB has a record of is the row TMDB wrote, so it is its own copy and
    there is no link pointing at it to find it by. The links find the other case:
    a title TMDB wrote that is also a copy of another, which is what a listing
    mixing titles leaves behind.
    """
    grouped: dict[UUID, list[Show]] = defaultdict(list)
    canonical_show_ids = set(canonical_show_ids)
    if not canonical_show_ids:
        return grouped

    titles = session.exec(
        select(Show)
        .join(Source)
        .join(Plugin)
        .where(
            col(Show.id).in_(canonical_show_ids),
            col(Show.deleted_at).is_(None),
            Plugin.key == TMDB_PLUGIN_KEY,
        ),
    ).all()
    for title in titles:
        grouped[title.id].append(title)

    rows = session.exec(
        select(ShowCanonicalShow.canonical_show_id, Show)  # type: ignore[call-overload]
        .select_from(ShowCanonicalShow)
        .join(Show, col(Show.id) == col(ShowCanonicalShow.show_id))
        .join(Source)
        .join(Plugin)
        .where(
            col(ShowCanonicalShow.canonical_show_id).in_(canonical_show_ids),
            col(Show.deleted_at).is_(None),
            Plugin.key == TMDB_PLUGIN_KEY,
        ),
    ).all()
    for canonical_show_id, show in rows:
        if show not in grouped[canonical_show_id]:
            grouped[canonical_show_id].append(show)
    return grouped


# TODO: Validate
def channel_show_for_show(
    session: Session,
    channel: Channel,
    show: Show,
) -> ChannelShow | None:
    """Return the row putting one of the titles `show` is a copy of on `channel`.

    A listing that mixes titles is on a channel under whichever of them was added,
    which need not be the title the listing is chiefly of, so every title it is a
    copy of is looked for. The chief title wins where the channel holds more than
    one of them, since it is the one the listing itself is about.
    """
    canonical_show_ids = show.canonical_show_ids
    if not canonical_show_ids:
        return None
    channel_shows = session.exec(
        select(ChannelShow).where(
            ChannelShow.channel_id == channel.id,
            col(ChannelShow.canonical_show_id).in_(canonical_show_ids),
        ),
    ).all()
    by_canonical_show = {
        channel_show.canonical_show_id: channel_show for channel_show in channel_shows
    }
    for canonical_show_id in canonical_show_ids:
        if channel_show := by_canonical_show.get(canonical_show_id):
            return channel_show
    return None


# TODO: Validate
def shows_for_channel_show(session: Session, channel_show: ChannelShow) -> list[Show]:
    """Return every website's copy of the title `channel_show` is about."""
    return shows_by_canonical_id(session, [channel_show.canonical_show_id])[
        channel_show.canonical_show_id
    ]


# TODO: Validate
def tmdb_shows_for_channel_show(
    session: Session,
    channel_show: ChannelShow,
) -> list[Show]:
    """Return TMDB's copies of the title `channel_show` is about.

    TMDB is not one of the websites a title can be watched on, so its copy is
    kept apart from them and only stands for what TMDB has a record of.
    """
    return tmdb_shows_by_canonical_id(session, [channel_show.canonical_show_id])[
        channel_show.canonical_show_id
    ]


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
    )
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
    )


# TODO: Validate
def add_urls_to_channel_import_queue(
    session: Session,
    channel: Channel,
    urls: Sequence[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    output: list[ChannelQueue] = []
    # Remove duplicates without changing the order allowing the output order to match
    # the input order.
    unique_urls = list(dict.fromkeys(url.strip() for url in urls))
    # Every existing entry is read in one query because a browse file can queue
    # thousands of URLs at once, which is a query each when they are read one by one.
    existing_records = {
        record.url: record
        for record in session.exec(
            select(ChannelQueue).where(
                ChannelQueue.channel_id == channel.id,
                col(ChannelQueue.url).in_(unique_urls),
            ),
        ).all()
    }

    for url in unique_urls:
        # If the entry already exists reset it to pending because the user may have
        # removed it from the channel or it may have failed to import for some reaosn.
        if queue_record := existing_records.get(url):
            queue_record.status = URLStatus.PENDING
        else:
            queue_record = ChannelQueue(
                channel_id=channel.id,
                url=url,
                status=URLStatus.PENDING,
            )
            session.add(queue_record)

        output.append(queue_record)

    session.commit()
    return output


# TODO: Validate
def update_whitelist(
    session: Session,
    channel_show: ChannelShow,
    config: WhitelistShowInput,
) -> None:
    """Update whitelist records for a channel show."""
    if config.is_whitelist is not None:
        channel_show.is_whitelist = config.is_whitelist

    existing_sources = {source.show_id for source in channel_show.source_filters}
    existing_seasons = {season.season_id for season in channel_show.season_filters}
    existing_episodes = {
        episode.canonical_episode_id for episode in channel_show.episode_filters
    }

    for source in config.sources:
        toggle_source_whitelist(
            session,
            channel_show,
            source.id,
            existing_sources,
            marked=source.marked,
        )
    for season in config.seasons:
        toggle_season_whitelist(
            session,
            channel_show,
            season.id,
            existing_seasons,
            marked=season.marked,
        )
    for episode in config.episodes:
        toggle_episode_whitelist(
            session,
            channel_show,
            _canonical_episode_id(session, episode.id),
            existing_episodes,
            marked=episode.marked,
            expires_at=episode.expires_at,
        )

    session.commit()


# TODO: Validate
def _canonical_episode_id(session: Session, episode_id: UUID) -> UUID | None:
    """Return the episode the copy `episode_id` is of, which is what a filter names.

    A copy of nothing is the episode itself, so it names itself.
    """
    return session.exec(
        select(canonical_id_column(Episode)).where(Episode.id == episode_id),  # type: ignore[call-overload]
    ).one()


# TODO: Validate
def _canonical_show_id_of_episode(
    session: Session,
    canonical_episode_id: UUID | None,
) -> UUID | None:
    """Return the title the episode `canonical_episode_id` names belongs to.

    An episode that is a copy of nothing hangs off a website's own listing rather
    than off the title, so the title is the one that listing is a copy of.
    """
    if canonical_episode_id is None:
        return None
    return session.exec(
        select(canonical_id_column(Show))
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(Episode.id == canonical_episode_id),
    ).one_or_none()


# TODO: Validate
def toggle_source_whitelist(
    session: Session,
    channel_show: ChannelShow,
    show_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    """Mark or unmark one website's copy of the title `channel_show` is about."""
    if marked and show_id not in existing:
        channel_show.source_filters.append(
            ChannelSourceFilter(
                channel_show_id=channel_show.id,
                show_id=show_id,
            ),
        )
    elif not marked and show_id in existing:
        existing_source = ChannelSourceFilter.get(session, channel_show, show_id)
        if existing_source:
            session.delete(existing_source)


# TODO: Validate
def toggle_season_whitelist(
    session: Session,
    channel_show: ChannelShow,
    season_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    """Add or drop the filter naming the season `season_id`."""
    if marked and season_id not in existing:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_id=season_id,
            ),
        )
    elif not marked and season_id in existing:
        existing_season = ChannelSeasonFilter.get(session, channel_show, season_id)
        if existing_season:
            session.delete(existing_season)


# TODO: Validate
def toggle_episode_whitelist(  # noqa: PLR0913 - mirrors toggle_season_whitelist plus expiry
    session: Session,
    channel_show: ChannelShow,
    canonical_episode_id: UUID | None,
    existing: set[UUID],
    *,
    marked: bool,
    expires_at: datetime | None = None,
) -> None:
    """Add, re-expire or drop the filter naming `canonical_episode_id`."""
    if canonical_episode_id is None:
        return
    if marked and canonical_episode_id not in existing:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                canonical_episode_id=canonical_episode_id,
                expires_at=expires_at,
            ),
        )
    elif marked and canonical_episode_id in existing:
        # Re-marking an existing entry updates its expiry.
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_show,
            canonical_episode_id,
        )
        if existing_episode:
            existing_episode.expires_at = expires_at
    elif not marked and canonical_episode_id in existing:
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_show,
            canonical_episode_id,
        )
        if existing_episode:
            session.delete(existing_episode)


# TODO: Validate
def blacklist_episode_on_channel(
    session: Session,
    channel: Channel,
    show: Show,
    episode_id: UUID,
    expires_at: datetime | None = None,
) -> ChannelShow:
    """Blacklist a single episode for `channel`.

    Gets or creates the `ChannelShow` for the title the episode belongs to, which
    is the episode's own answer rather than the listing's: a listing that mixes
    titles holds episodes of each of them, and hiding one of its episodes is about
    the title that episode is of. A newly created `ChannelShow` is a filter-only
    show (`is_blacklist_only=True`) in blacklist mode, so the title's other
    episodes are not pulled into the channel. Adds (or updates the expiry of) a
    `ChannelEpisodeFilter` for the episode, which covers that episode on every
    website the title is on.
    """
    canonical_episode_id = _canonical_episode_id(session, episode_id)
    canonical_show_id = (
        _canonical_show_id_of_episode(session, canonical_episode_id)
        or show.canonical_show_id
    )

    channel_show = ChannelShow.get(session, channel, canonical_show_id)
    if channel_show is None:
        channel_show = ChannelShow(
            channel_id=channel.id,
            canonical_show_id=canonical_show_id,
            is_whitelist=False,
            is_blacklist_only=True,
        )
        session.add(channel_show)

    existing_filter = ChannelEpisodeFilter.get(
        session,
        channel_show,
        canonical_episode_id,
    )
    if existing_filter is None:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                canonical_episode_id=canonical_episode_id,
                expires_at=expires_at,
            ),
        )
    else:
        existing_filter.expires_at = expires_at

    session.commit()
    session.refresh(channel_show)
    return channel_show


# TODO: Validate
def set_channel_order(
    session: Session,
    channel: Channel,
    episode_ids: Sequence[UUID],
) -> None:
    """Save the order `episode_ids` are in, as an order of episodes themselves.

    The ids each name one website's copy, which is what the channel was read as,
    but what is saved is an order of the episodes: the same episode arriving from
    another website next time takes the position already held for it. A copy that
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
def set_channel_combined_channels(
    session: Session,
    channel: Channel,
    combined_channels: Sequence[CombinedChannelInput],
) -> None:
    """Replace a `Channel`s `CombinedChannel`s with the given channels."""
    unique = {
        combined.id: combined
        for combined in combined_channels
        if combined.id != channel.id
    }
    channel.combined_channels = [
        ChannelCombinedChannel(
            channel_id=channel.id,
            combined_channel_id=combined.id,
        )
        for combined in unique.values()
    ]
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
