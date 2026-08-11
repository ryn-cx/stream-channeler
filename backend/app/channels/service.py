# TODO: Validate
from collections import defaultdict
from collections.abc import Collection, Iterable, Sequence
from datetime import datetime
from functools import cache
from uuid import UUID

from sqlmodel import Session, col, delete, select

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
    ChannelListOutput,
    ChannelOutput,
    ChannelsPublic,
    CombinedChannelInput,
    SortOptionOutput,
    WhitelistShowInput,
)
from app.episodes.models import Episode
from app.media.tmdb_fallback import TMDB_PLUGIN_KEY
from app.models import ZERO_LAST_SUFFIX
from app.plugins.models import Plugin
from app.schemas import RecordScope, ScopedReadOptions
from app.seasons.models import Season
from app.service import scoped_list_response
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User


# TODO: Validate
def shows_by_identifier(
    session: Session,
    identifiers: Collection[str],
) -> dict[str, list[Show]]:
    """Return every website's copy of each title in `identifiers`.

    A `ChannelShow` names a title rather than one website's copy of it, so the
    copies it stands for have to be looked up by the identifier they share.
    """
    grouped: dict[str, list[Show]] = defaultdict(list)
    if not identifiers:
        return grouped

    shows = session.exec(
        select(Show)
        .join(Source)
        .join(Plugin)
        .where(
            col(Show.show_identifier).in_(identifiers),
            col(Show.deleted_at).is_(None),
            # TMDB only supplies the metadata other websites left out, so its copy of
            # a title is never one of the websites the title can be watched on.
            Plugin.key != TMDB_PLUGIN_KEY,
        ),
    ).all()
    for show in shows:
        grouped[show.show_identifier].append(show)
    return grouped


# TODO: Validate
def tmdb_shows_by_identifier(
    session: Session,
    identifiers: Iterable[str],
) -> dict[str, list[Show]]:
    """Return TMDB's own copy of each title, keyed by the title's identifier.

    TMDB is not one of the websites a title can be watched on, so its copies are
    gathered apart from theirs rather than alongside them, and are only worth
    reading for a title that has no website copy to be read instead.
    """
    grouped: dict[str, list[Show]] = defaultdict(list)
    identifiers = set(identifiers)
    if not identifiers:
        return grouped

    shows = session.exec(
        select(Show)
        .join(Source)
        .join(Plugin)
        .where(
            col(Show.show_identifier).in_(identifiers),
            col(Show.deleted_at).is_(None),
            Plugin.key == TMDB_PLUGIN_KEY,
        ),
    ).all()
    for show in shows:
        grouped[show.show_identifier].append(show)
    return grouped


# TODO: Validate
def shows_for_channel_show(session: Session, channel_show: ChannelShow) -> list[Show]:
    """Return every website's copy of the title `channel_show` is about."""
    return shows_by_identifier(session, [channel_show.show_identifier])[
        channel_show.show_identifier
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
    return list(
        session.exec(
            select(Show)
            .join(Source)
            .join(Plugin)
            .where(
                col(Show.show_identifier) == channel_show.show_identifier,
                col(Show.deleted_at).is_(None),
                Plugin.key == TMDB_PLUGIN_KEY,
            ),
        ).all(),
    )


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
    existing_seasons = {
        season.season_identifier for season in channel_show.season_filters
    }
    existing_episodes = {
        episode.episode_identifier for episode in channel_show.episode_filters
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
            _season_identifier(session, season.id),
            existing_seasons,
            marked=season.marked,
        )
    for episode in config.episodes:
        toggle_episode_whitelist(
            session,
            channel_show,
            _episode_identifier(session, episode.id),
            existing_episodes,
            marked=episode.marked,
            expires_at=episode.expires_at,
        )

    session.commit()


# TODO: Validate
def _season_identifier(session: Session, season_id: UUID) -> str:
    """Return the identifier of the season `season_id`, whose key is not its id."""
    return session.exec(
        select(Season.season_identifier).where(Season.id == season_id),  # type: ignore[call-overload]
    ).one()


# TODO: Validate
def _episode_identifier(session: Session, episode_id: UUID) -> str:
    """Return the identifier of the episode `episode_id`, whose key is not its id."""
    return session.exec(
        select(Episode.episode_identifier).where(Episode.id == episode_id),  # type: ignore[call-overload]
    ).one()


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
    season_identifier: str,
    existing: set[str],
    *,
    marked: bool,
) -> None:
    if marked and season_identifier not in existing:
        channel_show.season_filters.append(
            ChannelSeasonFilter(
                channel_show_id=channel_show.id,
                season_identifier=season_identifier,
            ),
        )
    elif not marked and season_identifier in existing:
        existing_season = ChannelSeasonFilter.get(
            session,
            channel_show,
            season_identifier,
        )
        if existing_season:
            session.delete(existing_season)


# TODO: Validate
def toggle_episode_whitelist(  # noqa: PLR0913 - mirrors toggle_season_whitelist plus expiry
    session: Session,
    channel_show: ChannelShow,
    episode_identifier: str,
    existing: set[str],
    *,
    marked: bool,
    expires_at: datetime | None = None,
) -> None:
    if marked and episode_identifier not in existing:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_identifier=episode_identifier,
                expires_at=expires_at,
            ),
        )
    elif marked and episode_identifier in existing:
        # Re-marking an existing entry updates its expiry.
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_show,
            episode_identifier,
        )
        if existing_episode:
            existing_episode.expires_at = expires_at
    elif not marked and episode_identifier in existing:
        existing_episode = ChannelEpisodeFilter.get(
            session,
            channel_show,
            episode_identifier,
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

    Gets or creates the `ChannelShow` for the title `show` is a copy of. A newly created
    `ChannelShow` is a filter-only show (`is_blacklist_only=True`) in blacklist mode, so
    the title's other episodes are not pulled into the channel. Adds (or updates the
    expiry of) a `ChannelEpisodeFilter` for the episode, which covers that episode on
    every website the title is on.
    """
    channel_show = ChannelShow.get(session, channel, show)
    if channel_show is None:
        channel_show = ChannelShow(
            channel_id=channel.id,
            show_identifier=show.show_identifier,
            is_whitelist=False,
            is_blacklist_only=True,
        )
        session.add(channel_show)

    episode_identifier = _episode_identifier(session, episode_id)
    existing_filter = ChannelEpisodeFilter.get(
        session,
        channel_show,
        episode_identifier,
    )
    if existing_filter is None:
        channel_show.episode_filters.append(
            ChannelEpisodeFilter(
                channel_show_id=channel_show.id,
                episode_identifier=episode_identifier,
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
    session.exec(  # type: ignore[call-overload]
        delete(ChannelSavedEpisodeOrder).where(
            col(ChannelSavedEpisodeOrder.channel_id) == channel.id,
        ),
    )
    session.flush()
    for position, episode_id in enumerate(episode_ids):
        session.add(
            ChannelSavedEpisodeOrder(
                channel_id=channel.id,
                episode_id=episode_id,
                position=position,
            ),
        )
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
            label=_sort_option_label(model.__name__, field_name),
            # If this value does not match it should raise an error.
            model=model.__name__.lower(),  # type: ignore[arg-type]
            field=field_name,
        )
        for model in (Episode, Season, Show, Source, Plugin, Channel)
        for field_name in model.SORTABLE_FIELDS
    ]
    options.sort(key=lambda option: option.label)
    return options
