# TODO: Validate


import time
import uuid
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from datetime import datetime
from functools import cache
from random import shuffle
from typing import Any, NamedTuple
from uuid import UUID

from fastapi import HTTPException
from loguru import logger
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
from app.canonical_media.metadata import serve_as_canonical_episodes
from app.canonical_media.seasons import season_ids_by_episode
from app.channels.channel_scope import (
    child_channel_ids,
    readable_channels,
    resolve_channel_ids,
)
from app.channels.episode_selector import (
    EpisodeQueryBuilder,
    apply_user_episode_urls,
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
    BlacklistEpisodeInput,
    ChannelAdminCreate,
    ChannelAdminUpdate,
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelFavoriteUpdate,
    ChannelListOutput,
    ChannelOptions,
    ChannelOrderInput,
    ChannelOutput,
    ChannelPublicListOutput,
    ChannelQueueAdminOutput,
    ChannelQueueAdminUpdate,
    ChannelShowGroup,
    ChannelShowMembership,
    ChannelShowsOutput,
    ChannelShowStats,
    ChannelsPublic,
    CombinedChannelInput,
    CombinedChannelOutput,
    EpisodeWithDetails,
    MediaOwner,
    SortKeyInput,
    SortOptionOutput,
    WhitelistEpisodeLinkOutput,
    WhitelistEpisodeOutput,
    WhitelistEpisodesOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
    WhitelistSourceOutput,
)
from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.models import ZERO_LAST_SUFFIX, Visibility
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import Message, RecordScope, ScopedReadOptions
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.service import scoped_list_response
from app.shows.models import Show, ShowCanonicalShow
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.sources.service import get_or_create_custom_media_source
from app.users.models import User
from app.users.service import get_or_create_plugin_user

# How many of a season's episodes are read at once on the filter page.
WHITELIST_EPISODE_PAGE = 100


# One row of a channel's show list: the title it is listed under and the website's
# non-canonical row standing for it, since a non-canonical row that mixes titles is a
# row under each of them.
ChannelShowRow = tuple[uuid.UUID, uuid.UUID]


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


# TODO: Validate
def combined_channels_output(
    channel: Channel,
    session: Session,
) -> list[CombinedChannelOutput]:
    """Return a `Channel`'s `CombinedChannel`s."""
    result: list[CombinedChannelOutput] = []
    for combined in channel.combined_channels:
        combined_channel = session.get(Channel, combined.combined_channel_id)
        result.append(
            CombinedChannelOutput(
                id=combined.combined_channel_id,
                name=combined_channel.name if combined_channel else None,
            ),
        )
    return result


# TODO: Validate
def channel_episodes_output(
    channel: Channel,
    channel_options: ChannelOptions,
    user: User | None,
    session: Session,
) -> ChannelEpisodesOutput:
    """Read the episodes for a channel."""
    output = ChannelEpisodesOutput(
        episodes=[],
        seasons={},
        shows={},
        sources={},
        plugins={},
        channels={},
    )

    start = time.time()

    builder = EpisodeQueryBuilder(session, channel, channel_options, user)
    results = builder.get_episodes()

    unique_channel_ids = {
        channel_id for result in results for channel_id in result.channel_ids
    }
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = channel_output(channel_obj, user)

    source_keys: dict[uuid.UUID, str] = {}
    for result in results:
        episode = result.episode
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin
        source_keys[episode.id] = source.key

        extras: dict[str, Any] = {
            "channel_id": result.channel_id,
            "channel_ids": result.channel_ids,
        }
        # An episode nothing was minted for it to be linked to is the episode
        # itself, so it is served under its own id rather than under nothing.
        fields = episode.model_dump()
        fields["canonical_episode_id"] = canonical_id_of(episode)
        if result.latest_watch:
            extras["watch_date"] = result.latest_watch.watch_date
            extras["verified"] = result.latest_watch.verified
            extras["episode_watch_id"] = result.latest_watch.id

        output.episodes.append(
            EpisodeWithDetails(**fields, **extras),
        )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowPublic.model_validate(show)
        # The website is read off the row itself rather than off the id column on
        # the listing, which a title leaves empty. Only listings are ever here,
        # so the two say the same thing and only one of them says it in a type.
        if source.id not in output.sources:
            output.sources[source.id] = SourcePublic.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    serve_as_canonical_episodes(session, output.episodes)
    custom_source = apply_user_episode_urls(
        session,
        user,
        output.episodes,
        source_keys,
        builder.source_config,
        channel_options,
    )
    if custom_source:
        output.sources[custom_source.id] = SourcePublic.model_validate(custom_source)
        output.plugins[custom_source.plugin_id] = PluginOutput.model_validate(
            custom_source.plugin,
        )

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output


# TODO: Validate
def channel_shows_output(
    channel: Channel,
    user: User | None,
    session: Session,
) -> ChannelShowsOutput:
    """Read all shows for a channel, including those from its child channels."""
    output = ChannelShowsOutput()

    channel_ids = resolve_channel_ids(
        session,
        user,
        channel,
        child_channel_ids(channel),
    )
    channel_shows = session.exec(
        select(ChannelShow).where(col(ChannelShow.channel_id).in_(channel_ids)),
    ).all()
    # A `ChannelShow` is a title, so each one stands for every website's non-canonical
    # row of it.
    canonical_show_ids = {
        channel_show.canonical_show_id for channel_show in channel_shows
    }
    non_canonical_shows = shows_by_canonical_id(session, canonical_show_ids)

    # A title no website carries has only TMDB's own non-canonical row of it, and
    # leaving that out would leave the title out of the list it was added to, which is
    # the one place it would have shown that it is there at all.
    unwatchable = {
        canonical_show_id
        for canonical_show_id in canonical_show_ids
        if not non_canonical_shows[canonical_show_id]
    }
    non_canonical_shows.update(tmdb_shows_by_canonical_id(session, unwatchable))

    # A show can appear in several of the combined channels; deduplicate by the title it
    # is listed under and the non-canonical row it is. A show counts as a regular show
    # if any channel includes it normally, even when another channel only uses it for
    # filtering.
    regular_shows: dict[ChannelShowRow, ShowPublic] = {}
    filter_only_shows: dict[ChannelShowRow, ShowPublic] = {}
    # Regular shows kept per channel so they can be grouped by where they come from.
    shows_by_channel: dict[uuid.UUID, dict[ChannelShowRow, ShowPublic]] = {}
    channel_names: dict[uuid.UUID, str | None] = {}
    for channel_show in channel_shows:
        canonical_show_id = channel_show.canonical_show_id
        for show in non_canonical_shows[canonical_show_id]:
            source = show.source
            plugin = source.plugin

            # A non-canonical row is read as the title the channel holds rather than as
            # any other title it is of, since a listing that mixes titles is on a
            # channel under whichever of them was added. That is what gathers the
            # non-canonical rows of one title into the one row, and what the row's own
            # totals and missing fields are then filled in from.
            key = (canonical_show_id, show.id)
            update = {"canonical_show_id": canonical_show_id}

            if channel_show.is_blacklist_only:
                filter_only_shows.setdefault(
                    key,
                    ShowPublic.model_validate(show, update=update),
                )
            else:
                regular_shows.setdefault(
                    key,
                    ShowPublic.model_validate(show, update=update),
                )
                channel_group = shows_by_channel.setdefault(channel_show.channel_id, {})
                channel_group.setdefault(
                    key,
                    ShowPublic.model_validate(show, update=update),
                )
                channel_names.setdefault(
                    channel_show.channel_id,
                    channel_show.channel.name,
                )

            # TMDB is not somewhere a title can be watched, so it is not one of the
            # sources the list is filtered by and its icon does not stand beside a title
            # as though it were. A title it is the only non-canonical row of is left
            # with no icon, which is what having nowhere to watch it looks like.
            if source.id not in output.sources and plugin.key != TMDB_PLUGIN_KEY:
                output.sources[source.id] = SourcePublic.model_validate(source)

    output.shows = list(regular_shows.values())
    output.filter_only_shows = [
        show for key, show in filter_only_shows.items() if key not in regular_shows
    ]

    # The channel the request was made on comes first; the rest follow by name.
    # TODO: Validate
    def group_sort_key(group_channel_id: uuid.UUID) -> tuple[bool, str]:
        is_not_primary = group_channel_id != channel.id
        return (is_not_primary, (channel_names.get(group_channel_id) or "").lower())

    output.groups = [
        ChannelShowGroup(
            channel_id=group_channel_id,
            channel_name=channel_names.get(group_channel_id),
            shows=sorted(
                shows_by_channel[group_channel_id].values(),
                key=lambda show: (show.name or "").lower(),
            ),
        )
        for group_channel_id in sorted(shows_by_channel, key=group_sort_key)
    ]

    # Every title the channel holds rather than every title its non-canonical rows are
    # of, since a non-canonical row that mixes titles is listed under whichever of them
    # the channel was told to hold.
    output.stats = _channel_show_stats(session, canonical_show_ids)
    output.canonical_sources = _canonical_sources(session, canonical_show_ids)
    output.canonical_shows = _canonical_shows(session, canonical_show_ids)

    return output


# TODO: Validate
def channel_sources_output(
    channel: Channel,
    session: Session,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    non_canonical_shows = shows_by_canonical_id(
        session,
        {channel_show.canonical_show_id for channel_show in channel.shows},
    )
    for channel_show in channel.shows:
        for show in non_canonical_shows[channel_show.canonical_show_id]:
            source = show.source
            if source.id not in sources:
                sources[source.id] = SourcePublic.model_validate(source)

    custom_source = get_or_create_custom_media_source(session)
    sources.setdefault(
        custom_source.id,
        SourcePublic.model_validate(custom_source),
    )

    return list(sources.values())


# TODO: Validate
def channel_whitelist_output(
    session: Session,
    channel_show: ChannelShow,
) -> WhitelistShowOutput:
    """Read the sites and seasons of a title's filters in a channel.

    A filter is about the media rather than one website's non-canonical row of it, so
    every non-canonical row's seasons are listed, with the non-canonical rows of the
    same season collapsed into the one row the filter applies to. The episodes are read
    separately, a season at a time, since a title's whole catalogue is far more than the
    page opens on.
    """
    enabled_sources = {x.show_id for x in channel_show.source_filters}
    enabled_seasons = {x.season_id for x in channel_show.season_filters}

    shows = shows_for_channel_show(session, channel_show)
    tmdb_shows = tmdb_shows_for_channel_show(session, channel_show)
    if not shows and not tmdb_shows:
        raise HTTPException(status_code=404, detail="Show was not found on channel")

    # The websites' rows carrying each season, so a row can name the sites it
    # came from.
    season_show_ids = _listed_season_show_ids(session, channel_show, shows, tmdb_shows)

    sources = [
        WhitelistSourceOutput(
            show_id=show.id,
            source_id=show.source.id,
            source_name=show.source.name,
            favicon_url=show.source.favicon_url,
            show=ShowPublic.model_validate(show),
            filtered=show.id in enabled_sources,
            is_tmdb=show.source.plugin.key == TMDB_PLUGIN_KEY,
        )
        for show in [*shows, *tmdb_shows]
    ]

    # The rows are the title's own seasons rather than the websites' non-canonical rows
    # of them: a filter names a season of the title, and the title holds seasons no
    # website carries - one TMDB has announced, one only another site fills - which are
    # still seasons for the user to see rather than rows to leave out for having nothing
    # under them yet.
    title_seasons = session.exec(
        select(Season).where(
            Season.show_id == channel_show.canonical_show_id,
            col(Season.deleted_at).is_(None),
        ),
    ).all()
    season_rows = _seasons_by_id(session, title_seasons, season_show_ids)

    seasons: list[WhitelistSeasonOutput] = []
    listed_seasons: set[uuid.UUID] = set()

    # TODO: Validate
    def list_season(season_id: uuid.UUID) -> None:
        if season_id in listed_seasons:
            return
        listed_seasons.add(season_id)
        seasons.append(
            WhitelistSeasonOutput.model_validate(
                season_rows[season_id],
                update={
                    "filtered": season_id in enabled_seasons,
                    "show_ids": season_show_ids[season_id],
                },
            ),
        )

    for season in title_seasons:
        list_season(season.id)

    # A season the title has no row of is listed after the ones it does, in the
    # order the seasons themselves read in, so a page boundary and a listing
    # both fall the same way on every request.
    for season_id in sorted(
        season_show_ids,
        key=lambda key: _season_sort_key(season_rows[key]),
    ):
        list_season(season_id)

    return WhitelistShowOutput.model_validate(
        (shows or tmdb_shows)[0],
        update={
            "is_whitelist": channel_show.is_whitelist,
            "sources": sources,
            "seasons": seasons,
        },
    )


# TODO: Validate
def channel_whitelist_episodes_output(
    session: Session,
    channel_show: ChannelShow,
    season_id: uuid.UUID,
    offset: int = 0,
    limit: int = WHITELIST_EPISODE_PAGE,
) -> WhitelistEpisodesOutput:
    """Read one page of a season's episodes, as the filter page expands it.

    A filter is about the media rather than one website's non-canonical row of it, so
    the non-canonical rows of an episode are collapsed into the one row the filter
    applies to, and each non-canonical row is carried alongside as a link of its own.
    """
    enabled_episodes = {x.canonical_episode_id for x in channel_show.episode_filters}
    episode_expiries = {
        episode_filter.canonical_episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    # An episode is listed once under every season row carrying it, since two seasons
    # sharing an episode each have it to filter on. Only the non-canonical rows of it
    # under the same row are folded together.
    rows = _season_episode_rows(session, channel_show, season_id)
    representatives: dict[uuid.UUID, _SeasonEpisodeRow] = {}
    for row in rows:
        representatives.setdefault(row.canonical_episode_id, row)

    # Ordered and paged as the stored rows, since reading one as the schema is
    # work per episode and only the page being served is ever read.
    canonical_orders = _canonical_orders(session, representatives)
    page_rows = sorted(
        representatives.values(),
        key=lambda row: _episode_sort_key(
            row,
            canonical_orders.get(row.canonical_episode_id),
        ),
    )[offset : offset + limit]

    # Only the page being served is asked after: the links a row carries and the
    # reading of it as the media are both work per episode, and a season of a
    # thousand is not a season anybody reads at once.
    page_canonical_ids = {row.canonical_episode_id for row in page_rows}
    link_rows = [row for row in rows if row.canonical_episode_id in page_canonical_ids]
    episodes = _episodes_by_id(session, [row.id for row in link_rows])

    episode_source_filters = _episode_source_filters(channel_show)
    episode_show_ids: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    episode_links: dict[uuid.UUID, list[WhitelistEpisodeLinkOutput]] = defaultdict(list)
    for row in link_rows:
        if row.show_id not in episode_show_ids[row.canonical_episode_id]:
            episode_show_ids[row.canonical_episode_id].append(row.show_id)
        episode_source_filter = episode_source_filters.get(
            (row.canonical_episode_id, row.show_id),
        )
        episode_links[row.canonical_episode_id].append(
            WhitelistEpisodeLinkOutput.model_validate(
                episodes[row.id],
                update={
                    "show_id": row.show_id,
                    "episode_id": row.id,
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

    page = [
        WhitelistEpisodeOutput.model_validate(
            episodes[row.id],
            update={
                "season_id": season_id,
                "canonical_episode_id": row.canonical_episode_id,
                "filtered": row.canonical_episode_id in enabled_episodes,
                "expires_at": episode_expiries.get(row.canonical_episode_id),
                "show_ids": episode_show_ids[row.canonical_episode_id],
                "links": episode_links[row.canonical_episode_id],
            },
        )
        for row in page_rows
    ]

    serve_as_canonical_episodes(session, page)

    return WhitelistEpisodesOutput(episodes=page, total_count=len(representatives))


# TODO: Validate
def filtered_whitelist_episodes(
    session: Session,
    channel_show: ChannelShow,
) -> list[WhitelistEpisodeOutput]:
    """Read the episodes of a title that an entry names, whatever season they are in.

    The entries are what is being listed rather than the title's catalogue, so
    this stays small however many episodes the title has, which is what lets the
    blacklist be read without paging through everything it does not name.
    """
    enabled_episodes = {x.canonical_episode_id for x in channel_show.episode_filters}
    if not enabled_episodes:
        return []

    episode_expiries = {
        episode_filter.canonical_episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    media = _whitelist_media(session, channel_show)

    episodes: list[WhitelistEpisodeOutput] = []
    seen_episodes: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for season in [*media.site_seasons, *media.tmdb_seasons]:
        for episode in season.active_children:
            if episode.id not in media.listed_episode_ids:
                continue
            canonical_episode_id = canonical_id_of(episode)
            if canonical_episode_id not in enabled_episodes:
                continue
            episode_season_id = media.episode_seasons[episode.id]
            if (episode_season_id, canonical_episode_id) in seen_episodes:
                continue
            seen_episodes.add((episode_season_id, canonical_episode_id))
            episodes.append(
                WhitelistEpisodeOutput.model_validate(
                    episode,
                    update={
                        "season_id": episode_season_id,
                        "canonical_episode_id": canonical_episode_id,
                        "filtered": True,
                        "expires_at": episode_expiries.get(canonical_episode_id),
                        "show_ids": [],
                        "links": [],
                    },
                ),
            )

    canonical_orders = _canonical_orders(session, enabled_episodes)
    episodes.sort(
        key=lambda episode: _episode_sort_key(
            episode,
            canonical_orders.get(episode.canonical_episode_id),
        ),
    )
    episode_show_ids, episode_links = _episode_links_by_canonical_id(
        [*media.shows, *media.tmdb_shows],
        media.listed_episode_ids,
        _episode_source_filters(channel_show),
        enabled_episodes,
    )
    for episode_output in episodes:
        episode_output.show_ids = episode_show_ids[episode_output.canonical_episode_id]
        episode_output.links = episode_links[episode_output.canonical_episode_id]

    serve_as_canonical_episodes(session, episodes)
    return episodes


# TODO: Validate
def bulk_import_queue_urls(
    session: Session,
    current_user: User,
    entries: dict[uuid.UUID, list[str]],
) -> Message:
    """Add URLs to multiple channels' import queues at once."""
    channels_by_id = {
        channel.id: channel
        for channel in session.exec(
            select(Channel)
            .where(col(Channel.id).in_(entries.keys()))
            .where(Channel.user_id == current_user.id),
        ).all()
    }
    total_urls = 0
    for channel_id, urls in entries.items():
        if channel := channels_by_id.get(channel_id):
            add_urls_to_channel_import_queue(
                session=session,
                urls=urls,
                channel=channel,
            )
            total_urls += len(urls)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel {channel_id} not found",
            )
    return Message(message=f"{total_urls} URLs added across {len(entries)} channels")


# TODO: Validate
def favorite_channel(
    session: Session,
    current_user: User,
    channel: Channel,
) -> Message:
    """Favorite a `Channel` if it's readable by the `User`."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        session.add(ChannelFavorite(user_id=current_user.id, channel_id=channel.id))
        session.commit()
    return Message(message="Channel favorited successfully")


# TODO: Validate
def update_channel_favorite(
    session: Session,
    current_user: User,
    channel: Channel,
    favorite_in: ChannelFavoriteUpdate,
) -> Message:
    """Set the `User`'s private name/number for a favorited `Channel`.

    Favoriting the channel first if it isn't already, so personalizing it from the
    favorites view can never race against the favorite not yet existing.
    """
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        favorite = ChannelFavorite(user_id=current_user.id, channel_id=channel.id)
        session.add(favorite)
    favorite.name = favorite_in.name
    favorite.channel_number = favorite_in.channel_number
    session.commit()
    return Message(message="Favorite updated successfully")


# TODO: Validate
def unfavorite_channel(
    session: Session,
    current_user: User,
    channel: Channel,
) -> Message:
    """Remove a `Channel` from the `User`'s favorites."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is not None:
        session.delete(favorite)
        session.commit()
    return Message(message="Channel unfavorited successfully")


# TODO: Validate
def replace_combined_channels(
    session: Session,
    current_user: User,
    channel: Channel,
    combined_channels: list[CombinedChannelInput],
) -> Message:
    """Replace a `Channel`'s `CombinedChannel`s."""
    readable_ids = {
        readable.id
        for readable in readable_channels(
            session,
            current_user,
            [combined.id for combined in combined_channels],
        )
    }
    readable = [
        combined for combined in combined_channels if combined.id in readable_ids
    ]
    set_channel_combined_channels(session, channel, readable)
    return Message(message="Combined channels updated successfully")


# TODO: Validate
def update_whitelist_output(
    session: Session,
    whitelist_config: WhitelistShowInput,
    channel_show: ChannelShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    update_whitelist(session, channel_show, whitelist_config)
    # Build the response before any cleanup so it stays valid even if the
    # channel-show is removed below.
    output = channel_whitelist_output(session, channel_show)
    # A filter-only show that no longer hides anything serves no purpose, so drop it
    # to keep the channel's show list clean.
    if (
        channel_show.is_blacklist_only
        and not channel_show.source_filters
        and not channel_show.season_filters
        and not channel_show.episode_filters
    ):
        session.delete(channel_show)
        session.commit()
    return output


# TODO: Validate
def blacklist_episode_by_show_id(
    session: Session,
    channel: Channel,
    blacklist_in: BlacklistEpisodeInput,
) -> Message:
    """Blacklist a single episode for a `Channel`.

    When the show is not already on the channel a filter-only `ChannelShow` is
    created so the episode can be hidden without making the whole show a member of the
    channel. An optional `expires_at` makes the blacklist temporary.
    """
    # Show's primary key is (source_id, key), so look it up by its id column.
    show = session.exec(
        select(Show).where(Show.id == blacklist_in.show_id),
    ).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    blacklist_episode_on_channel(
        session=session,
        channel=channel,
        show=show,
        episode_id=blacklist_in.episode_id,
        expires_at=blacklist_in.expires_at,
    )
    return Message(message="Episode blacklisted successfully")


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


# TODO: Validate
def add_show(
    session: Session,
    channel: Channel,
    show: Show,
) -> Message:
    """Put a title, on every website it is on, onto a `Channel`."""
    add_show_to_channel(session, channel, show)
    return Message(message=f"{show.name} added to channel successfully")


# TODO: Validate
def remove_show(
    session: Session,
    channel_show: ChannelShow,
) -> Message:
    """Remove a title, on every website it is on, from a `Channel`."""
    shows = shows_for_channel_show(session, channel_show)
    # The title's own name is what is left to say when no website's non-canonical row of
    # it carries one, which is the case for a title only TMDB has a record of.
    canonical_show = session.exec(
        select(Show).where(Show.id == channel_show.canonical_show_id),
    ).first()
    name = next(
        (show.name for show in shows if show.name),
        canonical_show.name if canonical_show else None,
    )
    session.delete(channel_show)
    session.commit()
    return Message(message=f"{name} removed from channel successfully")


# TODO: Validate
def channel_queue(
    session: Session,
    channel: Channel,
) -> list[ChannelQueue]:
    """Read the URLs in a channel's import queue."""
    statement = (
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        # Descending order works better on the frontend because new URLs are appended to the
        # top of the list making it possible to immediately see the new URLs after adding
        # them without having to scroll down.
        .order_by(col(ChannelQueue.created_at).desc())
    )

    channels = session.exec(statement).all()

    return list(channels)


# TODO: Validate
def add_queue_urls(
    session: Session,
    channel: Channel,
    urls: list[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    return add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )


# TODO: Validate
def delete_queue_url(
    session: Session,
    channel: Channel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    queue_entry = session.exec(
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        .where(ChannelQueue.id == url_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


# TODO: Validate
def clear_completed_queue(
    session: Session,
    channel: Channel,
) -> Message:
    """Clear a channel's import queue."""
    for queue_entry in channel.queue:
        if queue_entry.status == URLStatus.IMPORTED:
            session.delete(queue_entry)

    session.commit()
    return Message(message="Import queue cleared successfully")


# TODO: Validate
def favorite_channel_ids(session: Session, current_user: User) -> list[uuid.UUID]:
    """List the ids of the `Channel`s the current `User` has favorited.

    Unreadable favorites are left in because this only drives the favorite toggle;
    the `favorites` scope of the list endpoint is what applies the read rules.
    """
    return list(
        session.exec(
            select(ChannelFavorite.channel_id).where(
                ChannelFavorite.user_id == current_user.id,
            ),
        ).all(),
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
    data.sort(key=lambda channel: channel.favorite_count, reverse=True)
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
def all_channel_queues(
    session: Session,
    current_user: User,
    owner: MediaOwner | None = None,
) -> list[ChannelQueueAdminOutput]:
    """List every `Channel`'s import queue entries, scoped by owner."""
    selector = (
        select(ChannelQueue, Channel, User.username)
        .join(Channel, col(Channel.id) == ChannelQueue.channel_id)
        .join(User, col(User.id) == Channel.user_id)
        .order_by(col(ChannelQueue.created_at).desc())
    )
    if not owner:
        selector = selector.where(Channel.user_id == current_user.id)
    else:
        plugin_user = get_or_create_plugin_user(session=session)
        if owner == MediaOwner.official:
            selector = selector.where(Channel.user_id == plugin_user.id)
        else:
            selector = selector.where(
                col(Channel.user_id).not_in([current_user.id, plugin_user.id]),
            )
    return [
        _channel_queue_admin_output(channel, username, queue_entry)
        for queue_entry, channel, username in session.exec(selector).all()
    ]


# TODO: Validate
def _queue_entry(session: Session, queue_id: uuid.UUID) -> ChannelQueue:
    entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return entry


# TODO: Validate
def admin_update_channel_queue(
    session: Session,
    queue_id: uuid.UUID,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    queue_entry = _queue_entry(session, queue_id)
    queue_entry.sqlmodel_update(queue_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(queue_entry)
    channel = session.get_one(Channel, queue_entry.channel_id)
    username = session.get_one(User, channel.user_id).username
    return _channel_queue_admin_output(channel, username, queue_entry)


# TODO: Validate
def admin_delete_channel_queue(session: Session, queue_id: uuid.UUID) -> Message:
    """Delete a `Channel`'s queue entry as an admin."""
    queue_entry = _queue_entry(session, queue_id)
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")
