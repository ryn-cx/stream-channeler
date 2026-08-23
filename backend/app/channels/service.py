# TODO: Validate
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from datetime import datetime
from functools import cache
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, delete, func, select

from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    links_of,
)
from app.canonical_media.filters import (
    is_canonical,
    is_non_canonical,
)
from app.channels.models import (
    Channel,
    ChannelCombinedChannel,
    ChannelEpisodeFilter,
    ChannelEpisodeSourceFilter,
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
    ChannelShowMembership,
    ChannelsPublic,
    CombinedChannelInput,
    SortKeyInput,
    SortOptionOutput,
    WhitelistShowInput,
)
from app.episodes.models import Episode
from app.models import ZERO_LAST_SUFFIX
from app.plugins.identifiers import TMDB_PLUGIN_KEY
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
    """Return every website's row for each canonical show in `canonical_show_ids`.

    A `ChannelShow` names a canonical show rather than one website's row, so the
    rows it stands for have to be looked up by the show they all stand for. A row
    carrying one of that show's episodes is one of them whatever it is linked to,
    since the episodes are the canonical show's own and carrying them is what
    being a place to watch it means.

    Every row linked to the canonical show is one of them as well. A row says
    which canonical shows it stands for before anything of it has been imported,
    and the episodes it does hold may be ones nothing was minted for them to
    stand for, so the link is the only word there is on either count. A row that
    mixes shows is linked to each of them alike and stands for every one.
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
    canonical_link = canonical_episode_link()
    carried = session.exec(
        select(canonical_season.show_id, Show)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(canonical_link, links_of(Episode, canonical_link))
        .join(
            canonical_episode,
            col(canonical_episode.id) == col(canonical_link.canonical_episode_id),
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
            # TMDB only supplies the metadata other websites left out, so its row
            # for a show is never one of the websites it can be watched on.
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .distinct(),
    ).all()
    for canonical_show_id, show in carried:
        add(canonical_show_id, show)

    linked = session.exec(
        select(ShowCanonicalShow.canonical_show_id, Show)  # type: ignore[call-overload]
        .select_from(Show)
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Show.id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(ShowCanonicalShow.canonical_show_id).in_(canonical_show_ids),
            is_non_canonical(Show),
            col(Show.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .distinct(),
    ).all()
    for canonical_show_id, show in linked:
        add(canonical_show_id, show)

    # A title nothing else holds a record of is the row that is the record, and
    # that row is where it is watched, so it stands for itself and no link points
    # at it. TMDB's own rows are gathered by `tmdb_shows_by_canonical_id`, since
    # TMDB is not somewhere anything is watched.
    standalone = session.exec(
        select(Show)
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Show.id).in_(canonical_show_ids),
            is_canonical(Show),
            col(Show.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        ),
    ).all()
    for show in standalone:
        add(show.id, show)

    return grouped


# TODO: Validate
def tmdb_shows_by_canonical_id(
    session: Session,
    canonical_show_ids: Iterable[UUID],
) -> dict[UUID, list[Show]]:
    """Return TMDB's own row for each canonical show, keyed by the show.

    TMDB is not one of the websites a show can be watched on, so its rows are
    gathered apart from theirs rather than alongside them.

    A canonical show TMDB has a record of is the row TMDB wrote, so it stands for
    itself and there is no link pointing at it to find it by. The links find the
    other case: a canonical show TMDB wrote that also stands for another, which is
    what a row mixing shows leaves behind.
    """
    grouped: dict[UUID, list[Show]] = defaultdict(list)
    canonical_show_ids = set(canonical_show_ids)
    if not canonical_show_ids:
        return grouped

    canonical_shows = session.exec(
        select(Show)
        .join(Source)
        .join(Plugin)
        .where(
            col(Show.id).in_(canonical_show_ids),
            col(Show.deleted_at).is_(None),
            Plugin.key == TMDB_PLUGIN_KEY,
        ),
    ).all()
    for canonical_show in canonical_shows:
        grouped[canonical_show.id].append(canonical_show)

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
def shows_for_channel_show(session: Session, channel_show: ChannelShow) -> list[Show]:
    """Return every website's row for the show `channel_show` is about."""
    return shows_by_canonical_id(session, [channel_show.canonical_show_id])[
        channel_show.canonical_show_id
    ]


# TODO: Validate
def tmdb_shows_for_channel_show(
    session: Session,
    channel_show: ChannelShow,
) -> list[Show]:
    """Return TMDB's rows for the canonical show `channel_show` is about.

    TMDB is not one of the websites a show can be watched on, so its row is
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
        favorite_count=favorite_count,
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
    existing_episode_sources = {
        (episode_source.canonical_episode_id, episode_source.show_id)
        for episode_source in channel_show.episode_source_filters
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
    for episode_source in config.episode_sources:
        toggle_episode_source_whitelist(
            session,
            channel_show,
            _canonical_episode_id(session, episode_source.episode_id),
            episode_source.show_id,
            existing_episode_sources,
            marked=episode_source.marked,
            expires_at=episode_source.expires_at,
        )

    session.commit()


# TODO: Validate
def _canonical_episode_id(session: Session, episode_id: UUID) -> UUID | None:
    """Return the canonical episode `episode_id` stands for, which a filter names.

    A row standing for nothing is the episode itself, so it names itself. A row
    standing for more than one names none of them, since a filter holds one
    episode and there is no saying which of them was meant.
    """
    canonical_link = canonical_episode_link()
    named = session.exec(
        select(canonical_episode_id_column(Episode, canonical_link))  # type: ignore[call-overload]
        .select_from(Episode)
        .outerjoin(canonical_link, links_of(Episode, canonical_link))
        .where(Episode.id == episode_id),
    ).all()
    if len(named) != 1:
        return None
    return named[0]


# TODO: Validate
def _canonical_show_ids_of_episode(
    session: Session,
    canonical_episode_id: UUID | None,
) -> set[UUID]:
    """Return the canonical shows `canonical_episode_id` belongs to.

    An episode of a canonical show belongs to that show alone. An episode that
    stands for nothing hangs off a website's own row rather than off a canonical
    show, and that row stands for each of its canonical shows alike, so it belongs
    to every one of them.
    """
    if canonical_episode_id is None:
        return set()
    own = session.exec(
        select(Show.id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(Episode.id == canonical_episode_id, is_canonical(Show)),
    ).all()
    if own:
        return set(own)
    linked = session.exec(
        select(ShowCanonicalShow.canonical_show_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(Season.show_id))
        .where(Episode.id == canonical_episode_id),
    ).all()
    return set(linked)


# TODO: Validate
def toggle_source_whitelist(
    session: Session,
    channel_show: ChannelShow,
    show_id: UUID,
    existing: set[UUID],
    *,
    marked: bool,
) -> None:
    """Mark or unmark one website's row for the show `channel_show` is about."""
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
def toggle_episode_source_whitelist(  # noqa: PLR0913 - mirrors toggle_episode_whitelist plus the website
    session: Session,
    channel_show: ChannelShow,
    canonical_episode_id: UUID | None,
    show_id: UUID,
    existing: set[tuple[UUID, UUID]],
    *,
    marked: bool,
    expires_at: datetime | None = None,
) -> None:
    """Add, re-expire or drop the entry naming `canonical_episode_id` on `show_id`."""
    if canonical_episode_id is None:
        return
    key = (canonical_episode_id, show_id)
    if marked and key not in existing:
        channel_show.episode_source_filters.append(
            ChannelEpisodeSourceFilter(
                channel_show_id=channel_show.id,
                canonical_episode_id=canonical_episode_id,
                show_id=show_id,
                expires_at=expires_at,
            ),
        )
        return
    if key not in existing:
        return
    existing_entry = ChannelEpisodeSourceFilter.get(
        session,
        channel_show,
        canonical_episode_id,
        show_id,
    )
    if not existing_entry:
        return
    if marked:
        # Re-marking an existing entry updates its expiry.
        existing_entry.expires_at = expires_at
    else:
        session.delete(existing_entry)


# TODO: Validate
def blacklist_episode_on_channel(
    session: Session,
    channel: Channel,
    show: Show,
    episode_id: UUID,
    expires_at: datetime | None = None,
) -> list[ChannelShow]:
    """Blacklist a single episode for `channel`.

    Gets or creates the `ChannelShow` for the canonical show the episode belongs
    to, which is the episode's own answer rather than its row's: a row that mixes
    shows holds episodes of each of them, and hiding one of its episodes is about
    the canonical show that episode belongs to. An episode nothing was minted for
    it to stand for has no canonical show of its own to answer with, and its row
    stands for each of its canonical shows alike, so the episode is hidden under
    every one of them. A newly created `ChannelShow` is a filter-only show
    (`is_blacklist_only=True`) in blacklist mode, so the canonical show's other
    episodes are not pulled into the channel. Adds (or updates the expiry of) a
    `ChannelEpisodeFilter` for the episode, which covers that episode on every
    website the canonical show is on.
    """
    canonical_episode_id = _canonical_episode_id(session, episode_id)
    canonical_show_ids = _canonical_show_ids_of_episode(
        session,
        canonical_episode_id,
    ) or set(show.canonical_show_ids)

    channel_shows: list[ChannelShow] = []
    for canonical_show_id in canonical_show_ids:
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
        channel_shows.append(channel_show)

    session.commit()
    for channel_show in channel_shows:
        session.refresh(channel_show)
    return channel_shows


# TODO: Validate
def channels_with_show_membership(
    session: Session,
    user: User,
    show: Show,
) -> list[ChannelShowMembership]:
    """Every `Channel` `user` owns, and whether it already holds `show`'s title.

    The title is what a channel holds rather than the one website's row asked
    about, so the row is read to the canonical shows it stands for first and a
    channel holding any of them is holding the title. A row that stands for
    nothing is the title itself, under its own id.

    One query rather than one per channel: the picker only needs a yes or no of
    each, which reading every channel's catalogue back answers the long way
    round.
    """
    canonical_show_ids = set(show.canonical_show_ids) or {show.id}

    carrying_channel_ids = set(
        session.exec(
            select(col(ChannelShow.channel_id)).where(
                col(ChannelShow.canonical_show_id).in_(canonical_show_ids),
                col(ChannelShow.is_blacklist_only).is_(False),
            ),
        ).all(),
    )
    channels = session.exec(
        select(Channel)
        .where(col(Channel.user_id) == user.id)
        .order_by(col(Channel.channel_number), col(Channel.name), col(Channel.id)),
    ).all()
    return [
        ChannelShowMembership(
            id=channel.id,
            name=channel.name,
            channel_number=channel.channel_number,
            carries_show=channel.id in carrying_channel_ids,
        )
        for channel in channels
    ]


# TODO: Validate
def add_show_to_channel(session: Session, channel: Channel, show: Show) -> None:
    canonical_show_ids = set(show.canonical_show_ids) or {show.id}

    channel_shows: list[ChannelShow] = []
    for canonical_show_id in canonical_show_ids:
        channel_show = ChannelShow.get(session, channel, canonical_show_id)
        if channel_show is None:
            channel_show = ChannelShow(
                channel_id=channel.id,
                canonical_show_id=canonical_show_id,
                is_whitelist=False,
                is_blacklist_only=False,
            )
            session.add(channel_show)
        else:
            channel_show.is_blacklist_only = False
        channel_shows.append(channel_show)

    session.commit()


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
