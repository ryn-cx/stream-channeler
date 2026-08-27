# TODO: Validate


import uuid
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import datetime
from functools import cache
from typing import Any, NamedTuple
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, distinct, exists, or_
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import Session, col, delete, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    canonical_id_of,
    links_of,
    links_to,
)
from app.canonical_media.filters import (
    is_canonical,
    is_non_canonical,
)
from app.canonical_media.keys import same_issuer_clause, tmdb_key_clause
from app.canonical_media.seasons import season_ids_by_episode
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
    ChannelQueueAdminOutput,
    ChannelShowMembership,
    ChannelShowStats,
    ChannelsPublic,
    CombinedChannelInput,
    SortKeyInput,
    SortOptionOutput,
    WhitelistEpisodeLinkOutput,
    WhitelistEpisodeOutput,
    WhitelistShowInput,
)
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.models import ZERO_LAST_SUFFIX
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import RecordScope, ScopedReadOptions
from app.seasons.models import Season
from app.service import scoped_list_response
from app.shows.models import Show, ShowCanonicalShow
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic
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


# TODO: Validate
def _channel_queue_admin_output(
    channel: Channel,
    username: str | None,
    queue_entry: ChannelQueue,
) -> ChannelQueueAdminOutput:
    return ChannelQueueAdminOutput.model_validate(
        queue_entry,
        update={
            "channel_name": channel.name,
            "channel_number": channel.channel_number,
            "user_id": channel.user_id,
            "username": username,
        },
    )


# An episode the website never ordered sits after every episode it did.
_UNORDERED = float("inf")


# TODO: Validate
def _canonical_shows(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ShowPublic]:
    """Return the title itself for each title the channel holds, keyed by it.

    A title is named by whoever catalogued it, which is TMDB wherever TMDB has a
    record of it, and that is the name it is read under rather than whatever any
    one website called its own row for it.
    """
    if not canonical_show_ids:
        return {}

    canonical_shows = session.exec(
        select(Show).where(col(Show.id).in_(canonical_show_ids)),
    ).all()
    return {
        canonical_show.id: ShowPublic.model_validate(canonical_show)
        for canonical_show in canonical_shows
    }


# TODO: Validate
def _canonical_sources(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, SourcePublic]:
    """Return the source each title itself was written by, keyed by the title.

    Which is TMDB wherever TMDB has a record of the title, and nothing where a
    website's listing is linked to a row minted for it to point at rather than of
    a title anything catalogued. Every row has a source now, including the minted
    ones, so what tells the two apart is who issued the key.
    """
    if not canonical_show_ids:
        return {}

    canonical_shows = session.exec(
        select(Show).where(
            col(Show.id).in_(canonical_show_ids),
            tmdb_key_clause(col(Show.key)),
        ),
    ).all()
    return {
        canonical_show.id: SourcePublic.model_validate(canonical_show.source)
        for canonical_show in canonical_shows
    }


# TODO: Validate
def _channel_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ChannelShowStats]:
    """Return what each title's seasons and episodes add up to.

    The same season and episode are carried by every website holding the title,
    so they are counted as the seasons and episodes they are rather than as the
    records holding them. Which title an episode counts towards is the episode's
    own answer, so a listing that mixes titles counts each of its episodes only
    towards the title that episode belongs to. An episode nothing was minted for
    it to be linked to has no such answer and counts towards the title its
    website's listing is linked to, under that website's own season.
    """
    if not canonical_show_ids:
        return {}

    canonical_episode = aliased(Episode)
    canonical_link = canonical_episode_link()
    rows = session.exec(
        select(
            Season.show_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(canonical_episode.id))),
        )
        .select_from(Season)
        .join(
            canonical_episode,
            col(canonical_episode.season_id) == col(Season.id),
        )
        .join(canonical_link, links_to(canonical_episode, canonical_link))
        .join(Episode, col(Episode.id) == col(canonical_link.episode_id))
        .where(
            is_canonical(canonical_episode),
            col(Season.show_id).in_(canonical_show_ids),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.show_id)),
    ).all()

    counts = {
        canonical_show_id: [season_count, episode_count]
        for canonical_show_id, season_count, episode_count in rows
    }
    for canonical_show_id, season_count, episode_count in _linked_show_stats(
        session,
        canonical_show_ids,
    ):
        totals = counts.setdefault(canonical_show_id, [0, 0])
        totals[0] += season_count
        totals[1] += episode_count

    for canonical_show_id, season_count, episode_count in _standalone_show_stats(
        session,
        canonical_show_ids,
    ):
        totals = counts.setdefault(canonical_show_id, [0, 0])
        totals[0] += season_count
        totals[1] += episode_count

    return {
        canonical_show_id: ChannelShowStats(
            season_count=season_count,
            episode_count=episode_count,
        )
        for canonical_show_id, (season_count, episode_count) in counts.items()
    }


# TODO: Validate
def _standalone_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> Sequence[tuple[uuid.UUID, int, int]]:
    """Return what a title that is its own listing holds.

    A title nothing else has a record of is the row that is the record, and that row is
    where it is watched, so its seasons and episodes are its own rather than
    non-canonical rows of anything and no link reaches them. TMDB's rows are left out: a
    title TMDB wrote is counted by what the websites carrying it hold.
    """
    return session.exec(
        select(
            Season.show_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Season)
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .where(
            col(Season.show_id).in_(canonical_show_ids),
            is_canonical(Show),
            Plugin.key != TMDB_PLUGIN_KEY,
            col(Show.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.show_id)),
    ).all()


# TODO: Validate
def _linked_show_stats(
    session: Session,
    canonical_show_ids: set[uuid.UUID],
) -> Sequence[tuple[uuid.UUID, int, int]]:
    """Return what the episodes no title has a record of add up to.

    Counted apart from the title's own seasons and episodes because there is
    nothing shared for them to be counted as: a website's record of one of these
    is the only record of it, so two websites carrying the same unmatched episode
    count as two.
    """
    linked_season = aliased(Season)
    linked_show = aliased(Show)
    return session.exec(
        select(
            ShowCanonicalShow.canonical_show_id,
            func.count(distinct(col(linked_season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Episode)
        .join(linked_season, col(linked_season.id) == col(Episode.season_id))
        .join(linked_show, col(linked_show.id) == col(linked_season.show_id))
        .join(ShowCanonicalShow, col(ShowCanonicalShow.show_id) == col(linked_show.id))
        .where(
            col(ShowCanonicalShow.canonical_show_id).in_(canonical_show_ids),
            is_canonical(Episode),
            is_non_canonical(linked_show),
            col(Episode.deleted_at).is_(None),
            col(linked_season.deleted_at).is_(None),
            col(linked_show.deleted_at).is_(None),
        )
        .group_by(col(ShowCanonicalShow.canonical_show_id)),
    ).all()


# TODO: Validate
class _EpisodeListingColumns(NamedTuple):
    link: Any
    canonical_episode: Any
    canonical_episode_id: Any
    listed_season_id: Any
    unlinked: Any


# TODO: Validate
def _episode_listing_columns() -> _EpisodeListingColumns:
    """Return what an `Episode` row is listed as, as columns to select or filter on.

    A row standing for exactly one episode is listed as that episode and under
    the season holding it; a row standing for none or for several answers for
    itself, since neither of the others is an episode it can be folded into.
    """
    link = canonical_episode_link()
    canonical_episode = aliased(Episode)
    return _EpisodeListingColumns(
        link=link,
        canonical_episode=canonical_episode,
        canonical_episode_id=canonical_episode_id_column(Episode, link),
        listed_season_id=func.coalesce(
            col(canonical_episode.season_id),
            col(Episode.season_id),
        ),
        unlinked=col(link.canonical_episode_id).is_(None),
    )


# TODO: Validate
def _listed_season_show_ids(
    session: Session,
    channel_show: ChannelShow,
    shows: Sequence[Show],
    tmdb_shows: Sequence[Show],
) -> dict[uuid.UUID, list[uuid.UUID]]:
    """Map each season to the websites' rows carrying it.

    A season a website announced and never filled is named by that website
    alone, since there is no episode under it to say who carries it.

    Which seasons a title has is a question about seasons rather than about
    episodes, so it is asked of the database as one: the rows come back a season
    apiece instead of an episode apiece, and a title of thirty thousand episodes
    costs what a title of thirty does.
    """
    show_order = {show.id: index for index, show in enumerate([*shows, *tmdb_shows])}
    site_show_ids = {show.id for show in shows}
    columns = _episode_listing_columns()

    carried = session.exec(
        select(columns.listed_season_id, Season.show_id)
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .outerjoin(columns.link, links_of(Episode, columns.link))
        .outerjoin(
            columns.canonical_episode,
            links_to(columns.canonical_episode, columns.link),
        )
        .where(
            col(Season.show_id).in_(show_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            or_(
                columns.canonical_episode_id.in_(
                    _title_episode_id_query(channel_show.canonical_show_id),
                ),
                and_(
                    columns.unlinked,
                    col(Season.show_id).in_(site_show_ids),
                ),
            ),
        )
        .distinct(),
    ).all()

    announced = session.exec(
        select(Season.id, Season.show_id).where(
            col(Season.show_id).in_(show_order),
            col(Season.deleted_at).is_(None),
            ~exists(
                select(Episode.id)
                .where(
                    col(Episode.season_id) == col(Season.id),
                    col(Episode.deleted_at).is_(None),
                )
                .correlate(Season),
            ),
        ),
    ).all()

    season_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for season_id, show_id in sorted(
        [*carried, *announced],
        key=lambda pair: show_order[pair[1]],
    ):
        if show_id not in season_show_ids[season_id]:
            season_show_ids[season_id].append(show_id)
    return season_show_ids


# TODO: Validate
def _episode_links_by_canonical_id(
    shows: Sequence[Show],
    listed_episode_ids: Collection[uuid.UUID],
    episode_source_filters: Mapping[
        tuple[uuid.UUID, uuid.UUID],
        ChannelEpisodeSourceFilter,
    ],
    wanted_episode_ids: Collection[uuid.UUID],
) -> tuple[
    dict[uuid.UUID, list[uuid.UUID]],
    dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]],
]:
    """Map each canonical episode of `wanted_episode_ids` to the rows carrying it."""
    episode_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_links: dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]] = defaultdict(list)
    for show in shows:
        for season in show.active_children:
            for episode in season.active_children:
                if episode.id not in listed_episode_ids:
                    continue
                episode_id = canonical_id_of(episode)
                if episode_id not in wanted_episode_ids:
                    continue
                if show.id not in episode_show_ids[episode_id]:
                    episode_show_ids[episode_id].append(show.id)
                episode_source_filter = episode_source_filters.get(
                    (episode_id, show.id),
                )
                episode_links[episode_id].append(
                    WhitelistEpisodeLinkOutput.model_validate(
                        episode,
                        update={
                            "show_id": show.id,
                            "episode_id": episode.id,
                            "filtered": episode_source_filter is not None,
                            "expires_at": (
                                episode_source_filter.expires_at
                                if episode_source_filter
                                else None
                            ),
                        },
                        from_attributes=True,
                    ),
                )
    return episode_show_ids, episode_links


# TODO: Validate
def _title_episode_ids(
    session: Session,
    canonical_show_id: uuid.UUID,
) -> set[uuid.UUID]:
    """Return the episodes the title itself holds, as against a website's own.

    A website files seasons under a title the title has no record of, and a
    canonical season is minted for each so its episodes have somewhere to hang,
    which leaves rows under the title that the title does not hold. They are
    told apart by who issued the season, the way `EpisodeQueryBuilder` tells
    them apart.
    """
    return set(session.exec(_title_episode_id_query(canonical_show_id)).all())


# TODO: Validate
def _title_episode_id_query(canonical_show_id: uuid.UUID) -> SelectOfScalar[uuid.UUID]:
    return (
        select(Episode.id)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .join(Show, col(Season.show_id) == col(Show.id))
        .where(
            Show.id == canonical_show_id,
            same_issuer_clause(col(Show.key), col(Season.key)),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
    )


# TODO: Validate
def _seasons_by_id(
    session: Session,
    loaded: Sequence[Season],
    season_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, Season]:
    """Return the row standing for each of `season_ids`, reading in what is missing."""
    seasons = {season.id: season for season in loaded}
    missing = set(season_ids) - seasons.keys()
    if missing:
        seasons.update(
            {
                season.id: season
                for season in session.exec(
                    select(Season).where(col(Season.id).in_(missing)),
                ).all()
            },
        )
    return seasons


# TODO: Validate
def _preload_episode_links(
    session: Session,
    seasons: Sequence[Season],
    episodes: Sequence[Episode],
) -> None:
    season_ids = [season.id for season in seasons]
    if not season_ids:
        return

    links_by_episode: dict[uuid.UUID, list[EpisodeCanonicalEpisode]] = defaultdict(list)
    for link in session.exec(
        select(EpisodeCanonicalEpisode)
        .join(Episode, col(EpisodeCanonicalEpisode.episode_id) == col(Episode.id))
        .where(col(Episode.season_id).in_(season_ids)),
    ).all():
        links_by_episode[link.episode_id].append(link)

    for episode in episodes:
        set_committed_value(
            episode,
            "canonical_episode_links",
            links_by_episode[episode.id],
        )


# TODO: Validate
class _WhitelistMedia(NamedTuple):
    """The rows a title's filters are read against, gathered once per request."""

    shows: list[Show]
    tmdb_shows: list[Show]
    site_seasons: list[Season]
    tmdb_seasons: list[Season]
    # Which season each episode belongs to, keyed by the website's own row.
    episode_seasons: dict[uuid.UUID, uuid.UUID]
    # The rows that stand for one of the title's own episodes, and so are the
    # ones a filter can name.
    listed_episode_ids: set[uuid.UUID]


# TODO: Validate
def _whitelist_media(
    session: Session,
    channel_show: ChannelShow,
) -> _WhitelistMedia:
    """Gather the websites' rows for the title `channel_show` is about."""
    shows = shows_for_channel_show(session, channel_show)
    # TMDB is not a website the title can be watched on, so it is not one of the
    # non-canonical rows the rows are built from, and only stands for the seasons it has
    # a record of, which is all an announced season no site has filled yet can be named
    # by. A title no website carries at all has nothing else to be listed from, so there
    # its record is the whole of what there is rather than the remainder.
    tmdb_shows = tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    # Every season and episode under those rows is walked below, which is a query
    # a season unless they are asked for together up front.
    session.exec(
        select(Show)
        .where(col(Show.id).in_([show.id for show in [*shows, *tmdb_shows]]))
        .options(selectinload(Show.seasons).selectinload(Season.episodes)),
    ).all()

    site_seasons = [season for show in shows for season in show.active_children]
    tmdb_seasons = [season for show in tmdb_shows for season in show.active_children]
    all_episodes = [
        episode
        for season in [*site_seasons, *tmdb_seasons]
        for episode in season.active_children
    ]
    _preload_episode_links(session, site_seasons + tmdb_seasons, all_episodes)
    # Which season an episode belongs to is the canonical episode's answer, since
    # a site can file an episode under a season the canonical hierarchy does not,
    # which is what puts a site's finale in another site's specials.
    episode_seasons = season_ids_by_episode(session, all_episodes)
    # Where a website files two titles under one listing it carries another title's
    # episodes as well. What a channel offers is the title's own episodes, so a
    # non-canonical row's episode is listed only where the episode it is linked to is
    # one of them. An episode that is linked to nothing is one the title had no record
    # of to match it against, and the link its listing carries is the only word there is
    # on what title it belongs to, so it is listed too.
    title_episode_ids = _title_episode_ids(session, channel_show.canonical_show_id)
    site_season_ids = {season.id for season in site_seasons}
    listed_episode_ids = {
        episode.id
        for episode in all_episodes
        if canonical_id_of(episode) in title_episode_ids
        or (
            not episode.canonical_episode_links and episode.season_id in site_season_ids
        )
    }
    return _WhitelistMedia(
        shows=shows,
        tmdb_shows=tmdb_shows,
        site_seasons=site_seasons,
        tmdb_seasons=tmdb_seasons,
        episode_seasons=episode_seasons,
        listed_episode_ids=listed_episode_ids,
    )


# TODO: Validate
def _episode_source_filters(
    channel_show: ChannelShow,
) -> dict[tuple[uuid.UUID, uuid.UUID], ChannelEpisodeSourceFilter]:
    """Return the entries naming an episode on one website alone.

    Read by the episode and the website together, since that pair is what such
    an entry is about.
    """
    return {
        (
            episode_source_filter.canonical_episode_id,
            episode_source_filter.show_id,
        ): episode_source_filter
        for episode_source_filter in channel_show.episode_source_filters
    }


# TODO: Validate
def _preload_canonical_episodes(session: Session, episodes: Sequence[Episode]) -> None:
    """Read in the episode each of `episodes` is linked to, in one query.

    `Episode.tmdb_id` walks from a row to the episode it is linked to, which is a
    query apiece where the rows are read one at a time. An `Episode` is keyed on
    its season and its own key rather than on `id`, so the walk cannot be
    answered out of the session and has to be asked for together up front.
    """
    episode_ids = [episode.id for episode in episodes]
    if not episode_ids:
        return
    session.exec(
        select(Episode)
        .where(col(Episode.id).in_(episode_ids))
        .options(
            selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()


# TODO: Validate
class _SeasonEpisodeRow(NamedTuple):
    id: uuid.UUID
    canonical_episode_id: uuid.UUID
    show_id: uuid.UUID
    sort_order: int | None


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
def _season_episode_rows(
    session: Session,
    channel_show: ChannelShow,
    season_id: uuid.UUID,
) -> list[_SeasonEpisodeRow]:
    shows = shows_for_channel_show(session, channel_show)
    tmdb_shows = tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    show_order = {show.id: index for index, show in enumerate([*shows, *tmdb_shows])}
    site_show_ids = {show.id for show in shows}

    columns = _episode_listing_columns()

    rows = session.exec(
        select(  # type: ignore[call-overload]
            Episode.id,
            Episode.sort_order,
            Season.show_id,
            columns.canonical_episode_id,
            columns.unlinked,
        )
        .select_from(Episode)
        .join(Season, col(Episode.season_id) == col(Season.id))
        .outerjoin(columns.link, links_of(Episode, columns.link))
        .outerjoin(
            columns.canonical_episode,
            links_to(columns.canonical_episode, columns.link),
        )
        .where(
            col(Season.show_id).in_(show_order),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
            columns.listed_season_id == season_id,
        ),
    ).all()

    title_episode_ids = _title_episode_ids(session, channel_show.canonical_show_id)
    listed = [
        _SeasonEpisodeRow(episode_id, canonical_id, show_id, sort_order)
        for episode_id, sort_order, show_id, canonical_id, unlinked in rows
        if canonical_id in title_episode_ids or (unlinked and show_id in site_show_ids)
    ]
    listed.sort(
        key=lambda row: (
            show_order[row.show_id],
            str(row.id),
            str(row.canonical_episode_id),
        ),
    )
    return listed


# TODO: Validate
def _episodes_by_id(
    session: Session,
    episode_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, Episode]:
    if not episode_ids:
        return {}
    episodes = session.exec(
        select(Episode)
        .where(col(Episode.id).in_(episode_ids))
        .options(
            selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()
    return {episode.id: episode for episode in episodes}
