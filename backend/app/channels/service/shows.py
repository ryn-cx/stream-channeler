# TODO: Validate


import uuid
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from uuid import UUID

from sqlalchemy import distinct, exists
from sqlalchemy.orm import aliased, selectinload
from sqlmodel import Session, col, func, select

from app.canonical_media.episodes import (
    canonical_episode_link,
    links_of,
    links_to,
)
from app.canonical_media.filters import (
    is_canonical,
    is_non_canonical,
)
from app.canonical_media.keys import tmdb_key_clause
from app.channels.channel_scope import (
    child_channel_ids,
    resolve_channel_ids,
)
from app.channels.models import (
    Channel,
    ChannelShow,
)
from app.channels.schemas import (
    ChannelShowGroup,
    ChannelShowMembership,
    ChannelShowsOutput,
    ChannelShowStats,
)
from app.episodes.models import Episode
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.shows.models import Show, ShowCanonicalShow
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.users.models import User

CHANNEL_SHOW_PAGE = 100


# One row of a channel's show list: the title it is listed under and the website's
# non-canonical row standing for it, since a non-canonical row that mixes titles is a
# row under each of them.
ChannelShowRow = tuple[uuid.UUID, uuid.UUID]


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

    copy_season = aliased(Season)
    canonical_episode = aliased(Episode)
    canonical_season = aliased(Season)
    canonical_link = canonical_episode_link()
    carried = session.exec(
        select(canonical_season.show_id, Show.id)
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

    linked = session.exec(
        select(ShowCanonicalShow.canonical_show_id, Show.id)
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

    # A title nothing else holds a record of is the row that is the record, and
    # that row is where it is watched, so it stands for itself and no link points
    # at it. TMDB's own rows are gathered by `tmdb_shows_by_canonical_id`, since
    # TMDB is not somewhere anything is watched.
    standalone = session.exec(
        select(Show.id)
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Show.id).in_(canonical_show_ids),
            is_canonical(Show),
            col(Show.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        ),
    ).all()

    pairs = [*carried, *linked, *[(show_id, show_id) for show_id in standalone]]
    shows_by_id = {
        show.id: show
        for show in session.exec(
            select(Show)
            .where(col(Show.id).in_({show_id for _canonical_id, show_id in pairs}))
            .options(selectinload(Show.source).selectinload(Source.plugin)),  # type: ignore[arg-type]
        ).all()
    }

    listed: dict[UUID, set[UUID]] = defaultdict(set)
    for canonical_show_id, show_id in pairs:
        if show_id in listed[canonical_show_id]:
            continue
        listed[canonical_show_id].add(show_id)
        grouped[canonical_show_id].append(shows_by_id[show_id])

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
def _paged_canonical_show_ids(
    session: Session,
    channel_ids: Collection[uuid.UUID],
    offset: int,
    limit: int,
) -> tuple[list[uuid.UUID], int]:
    total = session.exec(
        select(func.count(distinct(col(ChannelShow.canonical_show_id)))).where(
            col(ChannelShow.channel_id).in_(channel_ids),
            col(ChannelShow.is_blacklist_only).is_(False),
        ),
    ).one()

    canonical_show_ids = session.exec(
        select(ChannelShow.canonical_show_id)
        .join(
            Show,
            col(Show.id) == col(ChannelShow.canonical_show_id),
            isouter=True,
        )
        .where(
            col(ChannelShow.channel_id).in_(channel_ids),
            col(ChannelShow.is_blacklist_only).is_(False),
        )
        .group_by(col(ChannelShow.canonical_show_id), func.lower(col(Show.name)))
        .order_by(func.lower(col(Show.name)), col(ChannelShow.canonical_show_id))
        .offset(offset)
        .limit(limit),
    ).all()
    return list(canonical_show_ids), total


# TODO: Validate
def _filter_only_canonical_show_ids(
    session: Session,
    channel_ids: Collection[uuid.UUID],
) -> list[uuid.UUID]:
    regular = aliased(ChannelShow)
    return list(
        session.exec(
            select(ChannelShow.canonical_show_id)
            .where(
                col(ChannelShow.channel_id).in_(channel_ids),
                col(ChannelShow.is_blacklist_only).is_(True),
                ~exists(
                    select(regular.canonical_show_id)
                    .where(
                        col(regular.channel_id).in_(channel_ids),
                        col(regular.canonical_show_id)
                        == col(ChannelShow.canonical_show_id),
                        col(regular.is_blacklist_only).is_(False),
                    )
                    .correlate(ChannelShow),
                ),
            )
            .distinct(),
        ).all(),
    )


# TODO: Validate
def channel_show_stats_output(
    session: Session,
    canonical_show_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, ChannelShowStats]:
    return _channel_show_stats(session, set(canonical_show_ids))


# TODO: Validate
def channel_shows_output(
    channel: Channel,
    user: User | None,
    session: Session,
    offset: int = 0,
    limit: int = CHANNEL_SHOW_PAGE,
) -> ChannelShowsOutput:
    """Read all shows for a channel, including those from its child channels."""
    output = ChannelShowsOutput()

    channel_ids = resolve_channel_ids(
        session,
        user,
        channel,
        child_channel_ids(channel),
    )

    paged_show_ids, output.total = _paged_canonical_show_ids(
        session,
        channel_ids,
        offset,
        limit,
    )
    listed_show_ids = {
        *paged_show_ids,
        *_filter_only_canonical_show_ids(session, channel_ids),
    }
    channel_shows = session.exec(
        select(ChannelShow).where(
            col(ChannelShow.channel_id).in_(channel_ids),
            col(ChannelShow.canonical_show_id).in_(listed_show_ids),
        ),
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
    output.canonical_sources = _canonical_sources(session, canonical_show_ids)
    output.canonical_shows = _canonical_shows(session, canonical_show_ids)

    return output


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
