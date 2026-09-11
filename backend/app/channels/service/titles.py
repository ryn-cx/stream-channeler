# TODO: Validate


import uuid
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from uuid import UUID

from sqlalchemy import distinct, exists
from sqlalchemy.orm import aliased, selectinload
from sqlmodel import Session, col, func, select

from app.channels.channel_scope import (
    child_channel_ids,
    resolve_channel_ids,
)
from app.channels.models import (
    Channel,
    ChannelTitle,
)
from app.channels.schemas import (
    ChannelTitleGroup,
    ChannelTitleMembership,
    ChannelTitlesOutput,
    ChannelTitleStats,
)
from app.episodes.models import Episode
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.sources.models import Source
from app.sources.schemas import SourcePublic
from app.titles.models import Title, TitleTmdbTitle
from app.titles.schemas import TitlePublic
from app.tmdb_media.episodes import (
    links_of,
    links_to,
    tmdb_episode_link,
)
from app.tmdb_media.filters import (
    is_linked,
    is_not_linked,
)
from app.tmdb_media.tmdb import (
    tmdb_key_clause,
)
from app.users.models import User

CHANNEL_TITLE_PAGE = 100


# One row of a channel's title list: the title it is listed under and the website's
# non-canonical row standing for it, since a non-canonical row that mixes titles is a
# row under each of them.
ChannelTitleRow = tuple[uuid.UUID, uuid.UUID]


# TODO: Validate
def titles_by_tmdb_record_id(
    session: Session,
    tmdb_title_ids: Collection[UUID],
) -> dict[UUID, list[Title]]:
    """Return every website's row for each canonical title in `tmdb_title_ids`.

    A `ChannelTitle` names a canonical title rather than one website's row, so the
    rows it stands for have to be looked up by the title they all stand for. A row
    carrying one of that title's episodes is one of them whatever it is linked to,
    since the episodes are the canonical title's own and carrying them is what
    being a place to watch it means.

    Every row linked to the canonical title is one of them as well. A row says
    which canonical titles it stands for before anything of it has been imported,
    and the episodes it does hold may be ones nothing was minted for them to
    stand for, so the link is the only word there is on either count. A row that
    mixes titles is linked to each of them alike and stands for every one.
    """
    grouped: dict[UUID, list[Title]] = defaultdict(list)
    if not tmdb_title_ids:
        return grouped

    copy_season = aliased(Season)
    tmdb_episode = aliased(Episode)
    tmdb_season = aliased(Season)
    tmdb_link = tmdb_episode_link()
    carried = session.exec(
        select(tmdb_season.title_id, Title.id)
        .select_from(Episode)
        .join(tmdb_link, links_of(Episode, tmdb_link))
        .join(
            tmdb_episode,
            col(tmdb_episode.id) == col(tmdb_link.tmdb_episode_id),
        )
        .join(
            tmdb_season,
            col(tmdb_season.id) == col(tmdb_episode.season_id),
        )
        .join(copy_season, col(copy_season.id) == col(Episode.season_id))
        .join(Title, col(Title.id) == col(copy_season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(tmdb_season.title_id).in_(tmdb_title_ids),
            col(Episode.deleted_at).is_(None),
            col(copy_season.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
            # TMDB only supplies the metadata other websites left out, so its row
            # for a title is never one of the websites it can be watched on.
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .distinct(),
    ).all()

    linked = session.exec(
        select(TitleTmdbTitle.tmdb_title_id, Title.id)
        .select_from(Title)
        .join(TitleTmdbTitle, col(TitleTmdbTitle.title_id) == col(Title.id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(TitleTmdbTitle.tmdb_title_id).in_(tmdb_title_ids),
            is_linked(Title),
            col(Title.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        )
        .distinct(),
    ).all()

    # A title nothing else holds a record of is the row that is the record, and
    # that row is where it is watched, so it stands for itself and no link points
    # at it. TMDB's own rows are gathered by `tmdb_titles_by_id`, since
    # TMDB is not somewhere anything is watched.
    standalone = session.exec(
        select(Title.id)
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Title.id).in_(tmdb_title_ids),
            is_not_linked(Title),
            col(Title.deleted_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
        ),
    ).all()

    pairs = [*carried, *linked, *[(title_id, title_id) for title_id in standalone]]
    titles_by_id = {
        title.id: title
        for title in session.exec(
            select(Title)
            .where(col(Title.id).in_({title_id for _tmdb_record_id, title_id in pairs}))
            .options(selectinload(Title.source).selectinload(Source.plugin)),  # type: ignore[arg-type]
        ).all()
    }

    listed: dict[UUID, set[UUID]] = defaultdict(set)
    for tmdb_title_id, title_id in pairs:
        if title_id in listed[tmdb_title_id]:
            continue
        listed[tmdb_title_id].add(title_id)
        grouped[tmdb_title_id].append(titles_by_id[title_id])

    return grouped


# TODO: Validate
def tmdb_titles_by_id(
    session: Session,
    tmdb_title_ids: Iterable[UUID],
) -> dict[UUID, list[Title]]:
    """Return TMDB's own row for each canonical title, keyed by the title.

    TMDB is not one of the websites a title can be watched on, so its rows are
    gathered apart from theirs rather than alongside them.

    A canonical title TMDB has a record of is the row TMDB wrote, so it stands for
    itself and there is no link pointing at it to find it by. The links find the
    other case: a canonical title TMDB wrote that also stands for another, which is
    what a row mixing titles leaves behind.
    """
    grouped: dict[UUID, list[Title]] = defaultdict(list)
    tmdb_title_ids = set(tmdb_title_ids)
    if not tmdb_title_ids:
        return grouped

    tmdb_titles = session.exec(
        select(Title)
        .join(Source)
        .join(Plugin)
        .where(
            col(Title.id).in_(tmdb_title_ids),
            col(Title.deleted_at).is_(None),
            Plugin.key == TMDB_PLUGIN_KEY,
        ),
    ).all()
    for tmdb_title in tmdb_titles:
        grouped[tmdb_title.id].append(tmdb_title)

    rows = session.exec(
        select(TitleTmdbTitle.tmdb_title_id, Title)  # type: ignore[call-overload]
        .select_from(TitleTmdbTitle)
        .join(Title, col(Title.id) == col(TitleTmdbTitle.title_id))
        .join(Source)
        .join(Plugin)
        .where(
            col(TitleTmdbTitle.tmdb_title_id).in_(tmdb_title_ids),
            col(Title.deleted_at).is_(None),
            Plugin.key == TMDB_PLUGIN_KEY,
        ),
    ).all()
    for tmdb_title_id, title in rows:
        if title not in grouped[tmdb_title_id]:
            grouped[tmdb_title_id].append(title)
    return grouped


# TODO: Validate
def titles_from_channel_title(
    session: Session,
    channel_title: ChannelTitle,
) -> list[Title]:
    """Return every website's row for the title `channel_title` is about."""
    return titles_by_tmdb_record_id(session, [channel_title.tmdb_title_id])[
        channel_title.tmdb_title_id
    ]


# TODO: Validate
def tmdb_titles_from_channel_title(
    session: Session,
    channel_title: ChannelTitle,
) -> list[Title]:
    """Return TMDB's rows for the canonical title `channel_title` is about.

    TMDB is not one of the websites a title can be watched on, so its row is
    kept apart from them and only stands for what TMDB has a record of.
    """
    return tmdb_titles_by_id(session, [channel_title.tmdb_title_id])[
        channel_title.tmdb_title_id
    ]


# TODO: Validate
def channels_with_title_membership(
    session: Session,
    user: User,
    title: Title,
) -> list[ChannelTitleMembership]:
    """Every `Channel` `user` owns, and whether it already holds `title`'s title.

    The title is what a channel holds rather than the one website's row asked
    about, so the row is read to the canonical titles it stands for first and a
    channel holding any of them is holding the title. A row that stands for
    nothing is the title itself, under its own id.

    One query rather than one per channel: the picker only needs a yes or no of
    each, which reading every channel's catalogue back answers the long way
    round.
    """
    tmdb_title_ids = set(title.tmdb_title_ids) or {title.id}

    carrying_channel_ids = set(
        session.exec(
            select(col(ChannelTitle.channel_id)).where(
                col(ChannelTitle.tmdb_title_id).in_(tmdb_title_ids),
                col(ChannelTitle.is_blacklist_only).is_(False),
            ),
        ).all(),
    )
    channels = session.exec(
        select(Channel)
        .where(col(Channel.user_id) == user.id)
        .order_by(col(Channel.channel_number), col(Channel.name), col(Channel.id)),
    ).all()
    return [
        ChannelTitleMembership(
            id=channel.id,
            name=channel.name,
            channel_number=channel.channel_number,
            carries_title=channel.id in carrying_channel_ids,
        )
        for channel in channels
    ]


# TODO: Validate
def add_title_to_channel(session: Session, channel: Channel, title: Title) -> None:
    tmdb_title_ids = set(title.tmdb_title_ids) or {title.id}

    channel_titles: list[ChannelTitle] = []
    for tmdb_title_id in tmdb_title_ids:
        channel_title = ChannelTitle.get(session, channel, tmdb_title_id)
        if channel_title is None:
            channel_title = ChannelTitle(
                channel_id=channel.id,
                tmdb_title_id=tmdb_title_id,
                is_whitelist=False,
                is_blacklist_only=False,
            )
            session.add(channel_title)
        else:
            channel_title.is_blacklist_only = False
        channel_titles.append(channel_title)

    session.commit()


# TODO: Validate
def _tmdb_titles(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> dict[uuid.UUID, TitlePublic]:
    """Return the title itself for each title the channel holds, keyed by it.

    A title is named by whoever catalogued it, which is TMDB wherever TMDB has a
    record of it, and that is the name it is read under rather than whatever any
    one website called its own row for it.
    """
    if not tmdb_title_ids:
        return {}

    tmdb_titles = session.exec(
        select(Title).where(col(Title.id).in_(tmdb_title_ids)),
    ).all()
    return {
        tmdb_title.id: TitlePublic.model_validate(tmdb_title)
        for tmdb_title in tmdb_titles
    }


# TODO: Validate
def _tmdb_sources(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> dict[uuid.UUID, SourcePublic]:
    """Return the source each title itself was written by, keyed by the title.

    Which is TMDB wherever TMDB has a record of the title, and nothing where a
    website's listing is linked to a row minted for it to point at rather than of
    a title anything catalogued. Every row has a source now, including the minted
    ones, so what tells the two apart is who issued the key.
    """
    if not tmdb_title_ids:
        return {}

    tmdb_titles = session.exec(
        select(Title).where(
            col(Title.id).in_(tmdb_title_ids),
            tmdb_key_clause(col(Title.key)),
        ),
    ).all()
    return {
        tmdb_title.id: SourcePublic.model_validate(tmdb_title.source)
        for tmdb_title in tmdb_titles
    }


# TODO: Validate
def _channel_title_stats(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ChannelTitleStats]:
    """Return what each title's seasons and episodes add up to.

    The same season and episode are carried by every website holding the title,
    so they are counted as the seasons and episodes they are rather than as the
    records holding them. Which title an episode counts towards is the episode's
    own answer, so a listing that mixes titles counts each of its episodes only
    towards the title that episode belongs to. An episode nothing was minted for
    it to be linked to has no such answer and counts towards the title its
    website's listing is linked to, under that website's own season.
    """
    if not tmdb_title_ids:
        return {}

    tmdb_episode = aliased(Episode)
    tmdb_link = tmdb_episode_link()
    rows = session.exec(
        select(
            Season.title_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(tmdb_episode.id))),
        )
        .select_from(Season)
        .join(
            tmdb_episode,
            col(tmdb_episode.season_id) == col(Season.id),
        )
        .join(tmdb_link, links_to(tmdb_episode, tmdb_link))
        .join(Episode, col(Episode.id) == col(tmdb_link.episode_id))
        .where(
            is_not_linked(tmdb_episode),
            col(Season.title_id).in_(tmdb_title_ids),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.title_id)),
    ).all()

    counts = {
        tmdb_title_id: [season_count, episode_count]
        for tmdb_title_id, season_count, episode_count in rows
    }
    for tmdb_title_id, season_count, episode_count in _linked_title_stats(
        session,
        tmdb_title_ids,
    ):
        totals = counts.setdefault(tmdb_title_id, [0, 0])
        totals[0] += season_count
        totals[1] += episode_count

    for tmdb_title_id, season_count, episode_count in _standalone_title_stats(
        session,
        tmdb_title_ids,
    ):
        totals = counts.setdefault(tmdb_title_id, [0, 0])
        totals[0] += season_count
        totals[1] += episode_count

    return {
        tmdb_title_id: ChannelTitleStats(
            season_count=season_count,
            episode_count=episode_count,
        )
        for tmdb_title_id, (season_count, episode_count) in counts.items()
    }


# TODO: Validate
def _standalone_title_stats(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> Sequence[tuple[uuid.UUID, int, int]]:
    """Return what a title that is its own listing holds.

    A title nothing else has a record of is the row that is the record, and that row is
    where it is watched, so its seasons and episodes are its own rather than
    non-canonical rows of anything and no link reaches them. TMDB's rows are left out: a
    title TMDB wrote is counted by what the websites carrying it hold.
    """
    return session.exec(
        select(
            Season.title_id,
            func.count(distinct(col(Season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Season)
        .join(Title, col(Title.id) == col(Season.title_id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .join(Episode, col(Episode.season_id) == col(Season.id))
        .where(
            col(Season.title_id).in_(tmdb_title_ids),
            is_not_linked(Title),
            Plugin.key != TMDB_PLUGIN_KEY,
            col(Title.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Episode.deleted_at).is_(None),
        )
        .group_by(col(Season.title_id)),
    ).all()


# TODO: Validate
def _linked_title_stats(
    session: Session,
    tmdb_title_ids: set[uuid.UUID],
) -> Sequence[tuple[uuid.UUID, int, int]]:
    """Return what the episodes no title has a record of add up to.

    Counted apart from the title's own seasons and episodes because there is
    nothing shared for them to be counted as: a website's record of one of these
    is the only record of it, so two websites carrying the same unmatched episode
    count as two.
    """
    linked_season = aliased(Season)
    linked_title = aliased(Title)
    return session.exec(
        select(
            TitleTmdbTitle.tmdb_title_id,
            func.count(distinct(col(linked_season.id))),
            func.count(distinct(col(Episode.id))),
        )
        .select_from(Episode)
        .join(linked_season, col(linked_season.id) == col(Episode.season_id))
        .join(linked_title, col(linked_title.id) == col(linked_season.title_id))
        .join(
            TitleTmdbTitle,
            col(TitleTmdbTitle.title_id) == col(linked_title.id),
        )
        .where(
            col(TitleTmdbTitle.tmdb_title_id).in_(tmdb_title_ids),
            is_not_linked(Episode),
            is_linked(linked_title),
            col(Episode.deleted_at).is_(None),
            col(linked_season.deleted_at).is_(None),
            col(linked_title.deleted_at).is_(None),
        )
        .group_by(col(TitleTmdbTitle.tmdb_title_id)),
    ).all()


# TODO: Validate
def _paged_tmdb_title_ids(
    session: Session,
    channel_ids: Collection[uuid.UUID],
    offset: int,
    limit: int,
    query: str | None = None,
) -> tuple[list[uuid.UUID], int]:
    listed = [
        col(ChannelTitle.channel_id).in_(channel_ids),
        col(ChannelTitle.is_blacklist_only).is_(False),
    ]
    if query:
        listed.append(col(Title.name).ilike(f"%{query}%"))

    total = session.exec(
        select(func.count(distinct(col(ChannelTitle.tmdb_title_id))))
        .join(
            Title,
            col(Title.id) == col(ChannelTitle.tmdb_title_id),
            isouter=True,
        )
        .where(*listed),
    ).one()

    tmdb_title_ids = session.exec(
        select(ChannelTitle.tmdb_title_id)
        .join(
            Title,
            col(Title.id) == col(ChannelTitle.tmdb_title_id),
            isouter=True,
        )
        .where(*listed)
        .group_by(col(ChannelTitle.tmdb_title_id), func.lower(col(Title.name)))
        .order_by(func.lower(col(Title.name)), col(ChannelTitle.tmdb_title_id))
        .offset(offset)
        .limit(limit),
    ).all()
    return list(tmdb_title_ids), total


# TODO: Validate
def _filter_only_tmdb_title_ids(
    session: Session,
    channel_ids: Collection[uuid.UUID],
) -> list[uuid.UUID]:
    regular = aliased(ChannelTitle)
    return list(
        session.exec(
            select(ChannelTitle.tmdb_title_id)
            .where(
                col(ChannelTitle.channel_id).in_(channel_ids),
                col(ChannelTitle.is_blacklist_only).is_(True),
                ~exists(
                    select(regular.tmdb_title_id)
                    .where(
                        col(regular.channel_id).in_(channel_ids),
                        col(regular.tmdb_title_id)
                        == col(ChannelTitle.tmdb_title_id),
                        col(regular.is_blacklist_only).is_(False),
                    )
                    .correlate(ChannelTitle),
                ),
            )
            .distinct(),
        ).all(),
    )


# TODO: Validate
def channel_title_stats_output(
    session: Session,
    tmdb_title_ids: Collection[uuid.UUID],
) -> dict[uuid.UUID, ChannelTitleStats]:
    return _channel_title_stats(session, set(tmdb_title_ids))


# TODO: Validate
def channel_titles_output(  # noqa: PLR0913 - the listing is paged and searched
    channel: Channel,
    user: User | None,
    session: Session,
    offset: int = 0,
    limit: int = CHANNEL_TITLE_PAGE,
    query: str | None = None,
) -> ChannelTitlesOutput:
    """Read all titles for a channel, including those from its child channels."""
    output = ChannelTitlesOutput()

    channel_ids = resolve_channel_ids(
        session,
        user,
        channel,
        child_channel_ids(channel),
    )

    paged_title_ids, output.total = _paged_tmdb_title_ids(
        session,
        channel_ids,
        offset,
        limit,
        query,
    )
    listed_title_ids = {
        *paged_title_ids,
        *_filter_only_tmdb_title_ids(session, channel_ids),
    }
    channel_titles = session.exec(
        select(ChannelTitle).where(
            col(ChannelTitle.channel_id).in_(channel_ids),
            col(ChannelTitle.tmdb_title_id).in_(listed_title_ids),
        ),
    ).all()
    # A `ChannelTitle` is a title, so each one stands for every website's non-canonical
    # row of it.
    tmdb_title_ids = {
        channel_title.tmdb_title_id for channel_title in channel_titles
    }
    linked_titles = titles_by_tmdb_record_id(session, tmdb_title_ids)

    # A title no website carries has only TMDB's own non-canonical row of it, and
    # leaving that out would leave the title out of the list it was added to, which is
    # the one place it would have shown that it is there at all.
    unwatchable = {
        tmdb_title_id
        for tmdb_title_id in tmdb_title_ids
        if not linked_titles[tmdb_title_id]
    }
    linked_titles.update(tmdb_titles_by_id(session, unwatchable))

    # A title can appear in several of the combined channels; deduplicate by the title it
    # is listed under and the non-canonical row it is. A title counts as a regular title
    # if any channel includes it normally, even when another channel only uses it for
    # filtering.
    regular_titles: dict[ChannelTitleRow, TitlePublic] = {}
    filter_only_titles: dict[ChannelTitleRow, TitlePublic] = {}
    # Regular titles kept per channel so they can be grouped by where they come from.
    titles_by_channel: dict[uuid.UUID, dict[ChannelTitleRow, TitlePublic]] = {}
    channel_names: dict[uuid.UUID, str | None] = {}
    for channel_title in channel_titles:
        tmdb_title_id = channel_title.tmdb_title_id
        for title in linked_titles[tmdb_title_id]:
            source = title.source
            plugin = source.plugin

            # A non-canonical row is read as the title the channel holds rather than as
            # any other title it is of, since a listing that mixes titles is on a
            # channel under whichever of them was added. That is what gathers the
            # non-canonical rows of one title into the one row, and what the row's own
            # totals and missing fields are then filled in from.
            key = (tmdb_title_id, title.id)
            update = {"tmdb_title_id": tmdb_title_id}

            if channel_title.is_blacklist_only:
                filter_only_titles.setdefault(
                    key,
                    TitlePublic.model_validate(title, update=update),
                )
            else:
                regular_titles.setdefault(
                    key,
                    TitlePublic.model_validate(title, update=update),
                )
                channel_group = titles_by_channel.setdefault(
                    channel_title.channel_id,
                    {},
                )
                channel_group.setdefault(
                    key,
                    TitlePublic.model_validate(title, update=update),
                )
                channel_names.setdefault(
                    channel_title.channel_id,
                    channel_title.channel.name,
                )

            # TMDB is not somewhere a title can be watched, so it is not one of the
            # sources the list is filtered by and its icon does not stand beside a title
            # as though it were. A title it is the only non-canonical row of is left
            # with no icon, which is what having nowhere to watch it looks like.
            if source.id not in output.sources and plugin.key != TMDB_PLUGIN_KEY:
                output.sources[source.id] = SourcePublic.model_validate(source)

    output.titles = list(regular_titles.values())
    output.filter_only_titles = [
        title for key, title in filter_only_titles.items() if key not in regular_titles
    ]

    # The channel the request was made on comes first; the rest follow by name.
    # TODO: Validate
    def group_sort_key(group_channel_id: uuid.UUID) -> tuple[bool, str]:
        is_not_primary = group_channel_id != channel.id
        return (is_not_primary, (channel_names.get(group_channel_id) or "").lower())

    output.groups = [
        ChannelTitleGroup(
            channel_id=group_channel_id,
            channel_name=channel_names.get(group_channel_id),
            titles=sorted(
                titles_by_channel[group_channel_id].values(),
                key=lambda title: (title.name or "").lower(),
            ),
        )
        for group_channel_id in sorted(titles_by_channel, key=group_sort_key)
    ]

    # Every title the channel holds rather than every title its non-canonical rows are
    # of, since a non-canonical row that mixes titles is listed under whichever of them
    # the channel was told to hold.
    output.tmdb_sources = _tmdb_sources(session, tmdb_title_ids)
    output.tmdb_titles = _tmdb_titles(session, tmdb_title_ids)

    return output


# TODO: Validate
def add_title(
    session: Session,
    channel: Channel,
    title: Title,
) -> Message:
    """Put a title, on every website it is on, onto a `Channel`."""
    add_title_to_channel(session, channel, title)
    return Message(message=f"{title.name} added to channel successfully")


# TODO: Validate
def remove_title(
    session: Session,
    channel_title: ChannelTitle,
) -> Message:
    """Remove a title, on every website it is on, from a `Channel`."""
    titles = titles_from_channel_title(session, channel_title)
    # The title's own name is what is left to say when no website's non-canonical row of
    # it carries one, which is the case for a title only TMDB has a record of.
    tmdb_title = session.exec(
        select(Title).where(Title.id == channel_title.tmdb_title_id),
    ).first()
    name = next(
        (title.name for title in titles if title.name),
        tmdb_title.name if tmdb_title else None,
    )
    session.delete(channel_title)
    session.commit()
    return Message(message=f"{name} removed from channel successfully")
