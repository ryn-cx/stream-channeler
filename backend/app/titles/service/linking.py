# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

import re
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, delete, or_, select, update
from sqlmodel.sql.expression import SelectOfScalar

from app.channels.models import ChannelTitle
from app.episodes.linking import EpisodeLinkerV2
from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
    EpisodeTmdbEpisode,
    is_manual_note,
)
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title, TitleTmdbTitle
from app.titles.schemas import AutomaticLinkGroupOutput
from app.tmdb_media.filters import is_not_linked
from app.utils import tz_datetime
from plugins.utils.manage_plugins import plugins

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import TMDBLookupInfo

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def tmdb_titles_from_lookup_info(
    session: Session,
    lookup_infos: Sequence[TMDBLookupInfo],
) -> set[Title]:
    from plugins.TMDB import TMDB  # noqa: PLC0415

    tmdb_plugin = TMDB(session)
    tmdb_titles: set[Title] = set()
    for lookup_info in lookup_infos:
        search_results = tmdb_plugin.import_search(
            lookup_info.name,
            lookup_info.media_type,
            lookup_info.year,
        )
        for search_result in search_results:
            tmdb_titles.add(search_result.title)
    return tmdb_titles


# TODO: Validate
def tmdb_titles_from_title(session: Session, title: Title) -> set[Title]:
    plugin_classes_by_key = {plugin.plugin_name(): plugin for plugin in plugins}
    plugin_key = title.source.plugin.key
    plugin_class = plugin_classes_by_key[plugin_key]
    plugin_instance = plugin_class(session, title.source.plugin)
    return tmdb_titles_from_lookup_info(
        session,
        plugin_instance.tmdb_lookup_info(title),
    )


# TODO: Validate
def link_new_title_to_tmdb(session: Session, title: Title) -> None:
    if title.link_status:
        msg = "link_new_title_to_tmdb should only be called on new titles."
        raise ValueError(msg)
    if title.source.plugin.key == "TMDB":
        msg = "link_new_title_to_tmdb should not be called on TMDB titles."
        raise ValueError(msg)

    for tmdb_title in tmdb_titles_from_title(session, title):
        note = "Automatic: Found match on TMDB"
        link_unlinked_title_to_tmdb(session, title, tmdb_title, note)
    if title.tmdb_title_links:
        title.link_status = "Linked"
    else:
        title.link_status = "No Match Found"
    session.add(title)
    session.commit()


# TODO: Validate
def _remove_unmatched_for_plugin(
    session: Session,
    title: Title,
    tmdb_title: Title,
) -> None:
    from app.titles.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_titles,
    )

    remove_plugin_unmatched_titles(session, tmdb_title.id, title.source.plugin.key)


# TODO: Validate
def link_unlinked_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleTmdbTitle:
    """Link an unlinked title to a TMDB title and update all channels containing it.

    Channels that include the unlinked title will have it replaced with the TMDB
    title."""
    channel_titles = session.exec(
        select(ChannelTitle).where(
            ChannelTitle.tmdb_title_id == title.id,
        ),
    ).all()
    channel_titles_by_channel_id = {
        channel_title.channel_id: channel_title for channel_title in channel_titles
    }
    channels_with_title_and_tmdb_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                col(ChannelTitle.tmdb_title_id) == tmdb_title.id,
                col(ChannelTitle.channel_id).in_(
                    list(channel_titles_by_channel_id),
                ),
            ),
        ).all(),
    )

    # Replace the unlinked title with the TMDB title.
    for channel_id, channel_title in channel_titles_by_channel_id.items():
        if channel_id in channels_with_title_and_tmdb_title:
            continue
        session.add(
            ChannelTitle(
                channel_id=channel_id,
                tmdb_title_id=tmdb_title.id,
                is_whitelist=channel_title.is_whitelist,
                is_blacklist_only=channel_title.is_blacklist_only,
            ),
        )

    # Remove the unlinked title from all channels.
    for channel_title in channel_titles:
        session.delete(channel_title)
    session.flush()

    link = TitleTmdbTitle(
        title_id=title.id,
        tmdb_title_id=tmdb_title.id,
        note=note,
        manual_tmdb_link=is_manual_note(note),
    )
    session.add(link)
    session.flush()
    _remove_unmatched_for_plugin(session, title, tmdb_title)
    session.expire(title, ["tmdb_title_links", "is_linked"])
    _old_relink_episode(session, title)
    return link


# TODO: Validate
def _old_relink_episodes(session: Session, tmdb_title: Title) -> None:
    """Match every non-canonical row of `tmdb_title` against it again."""
    for link in list(tmdb_title.linked_title_links):
        _old_relink_episode(session, link.linked_title)


# TODO: Validate
def _old_relink_episode(
    session: Session,
    linked_title: Title,
) -> None:
    episodes = _old_relinkable_episodes(session, linked_title)
    dropped_links = _old_clear_tmdb_episode_links(session, episodes)
    linker = EpisodeLinkerV2(session, linked_title, dropped_links)
    with session.no_autoflush:
        linker.link_titles()
    for link in dropped_links.values():
        session.delete(link)


# TODO: Validate
def _title_episodes(session: Session, title: Title) -> list[Episode]:
    if "seasons" in instance_state(title).unloaded or any(
        "episodes" in instance_state(season).unloaded for season in title.seasons
    ):
        session.exec(
            select(Season)
            .where(col(Season.title_id) == title.id)
            .options(
                selectinload(Season.episodes),  # type: ignore[arg-type]
            ),
        ).all()
    return [
        episode
        for season in title.active_children
        for episode in season.active_children
    ]


# TODO: Validate
def _old_relinkable_episodes(session: Session, title: Title) -> list[Episode]:
    return [
        episode
        for episode in _title_episodes(session, title)
        if episode.tmdb_episode_validated_at is None
    ]


# TODO: Validate
def _old_clear_tmdb_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> dict[tuple[uuid.UUID, uuid.UUID], EpisodeTmdbEpisode]:
    _old_preload_tmdb_episode_links(session, episodes)
    # A link a `User` settled themselves is left where it is, so what is cleared
    # is only ever a guess an automatic match made.
    dropped_links: dict[tuple[uuid.UUID, uuid.UUID], EpisodeTmdbEpisode] = {}
    for episode in episodes:
        kept_links = [
            link for link in episode.tmdb_episode_links if link.manual_tmdb_link
        ]
        if len(kept_links) == len(episode.tmdb_episode_links):
            continue
        for link in episode.tmdb_episode_links:
            if not link.manual_tmdb_link:
                dropped_links[link.episode_id, link.tmdb_episode_id] = link
        set_committed_value(episode, "tmdb_episode_links", kept_links)
    return dropped_links


# TODO: Validate
def _old_reread_in_new_order(session: Session, title: Title) -> None:
    """Read `title` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    logger.info(f"Rereading title in a new order: {title.name or title.key}")
    TMDB(session).update_title(title)


# TODO: Validate
def _old_preload_tmdb_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> None:
    unread = [
        episode.id
        for episode in episodes
        if "tmdb_episode_links" in instance_state(episode).unloaded
    ]
    if not unread:
        return
    session.exec(
        select(Episode)
        .where(col(Episode.id).in_(unread))
        .options(
            selectinload(Episode.tmdb_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeTmdbEpisode.tmdb_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()


# TODO: Validate
def old_relink_title(session: Session, title: Title) -> Title:
    if not title.is_linked:
        _old_relink_episodes(session, title)
    else:
        _old_relink_episode(session, title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def _old_validate_titles(title: Title, tmdb_title: Title) -> None:
    """Validate that `title` and `tmdb_title` can be linked.

    The title cannot have any other canonical titles linked to it and it cannot be a TMDB
    title.

    The TMDB title must be canonical TMDB title."""
    if tmdb_title.is_linked:
        message = f"{tmdb_title} is not a canonical title."
        raise ValueError(message)
    if tmdb_title.source.plugin.key != TMDB_PLUGIN_KEY:
        message = f"{tmdb_title} is not a TMDB title."
        raise ValueError(message)
    if title.source.plugin.key == TMDB_PLUGIN_KEY:
        message = f"{title} is a TMDB title."
        raise ValueError(message)
    if title.linked_title_links:
        message = f"{title} has other titles linked to it."
        raise ValueError(message)


# TODO: Validate
def old_link_title_by_tmdb_lookups(
    session: Session,
    unlinked_title: Title,
    lookup_infos: Sequence[TMDBLookupInfo],
) -> None:
    """Link a plugin's title to TMDB using tmdb_lookup_info."""
    tmdb_titles = tmdb_titles_from_lookup_info(session, lookup_infos)
    for tmdb_title in tmdb_titles:
        note = "Automatic: Found match on TMDB"
        old_link_title_to_tmdb(session, unlinked_title, tmdb_title, note)


# TODO: Validate
def old_link_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleTmdbTitle:
    """Link a title to TMDB then links the title's episodes to TMDB.

    Will not remove any existing title links."""
    _old_validate_titles(title, tmdb_title)
    if not title.is_linked:
        return link_unlinked_title_to_tmdb(session, title, tmdb_title, note)

    _remove_unmatched_for_plugin(session, title, tmdb_title)
    for tmdb_link in title.tmdb_title_links:
        if tmdb_link.tmdb_title_id == tmdb_title.id:
            return tmdb_link

    link = TitleTmdbTitle(
        title_id=title.id,
        tmdb_title_id=tmdb_title.id,
        note=note,
        manual_tmdb_link=is_manual_note(note),
    )
    session.add(link)
    session.flush()
    session.expire(title, ["tmdb_title_links", "is_linked"])
    _old_relink_episode(session, title)
    return link


# TODO: Validate
def old_link_title_to_tmdb_title(
    session: Session,
    website_title: Title,
    tmdb_title: Title,
) -> Title:
    if website_title.linked_title_links:
        message = "A title other titles are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    old_link_title_to_tmdb(
        session,
        website_title,
        tmdb_title,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    website_title.tmdb_title_validated_at = tz_datetime.now()
    session.add(website_title)

    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def old_link_title_to_tmdb_title_from_url(
    session: Session,
    website_title: Title,
    tmdb_url: str,
) -> Title:
    """Import the TMDB title at `tmdb_url` and link `website_title` to it."""
    from plugins.TMDB import TMDB  # noqa: PLC0415

    stripped_url = tmdb_url.strip()
    if not _TMDB_TITLE_URL.search(stripped_url):
        raise HTTPException(
            status_code=400,
            detail=f"{tmdb_url} is not the address of a TMDB film or series",
        )

    imported_titles = TMDB(session).validate_and_import_url(stripped_url)
    tmdb_title = session.exec(
        select(Title).where(
            is_not_linked(Title),
            Title.key == imported_titles[0].title.key,
        ),
    ).one()
    return old_link_title_to_tmdb_title(session, website_title, tmdb_title)


# TODO: Validate
def old_import_linked_title_from_url(
    session: Session,
    tmdb_title: Title,
    title_url: str,
) -> Title:
    """Import the title at `title_url` and link it to `tmdb_title`."""
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import get_plugin_from_url  # noqa: PLC0415

    stripped_url = title_url.strip()
    if tmdb_title.is_linked:
        message = "A title linked to a canonical title cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = get_plugin_from_url(stripped_url)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {stripped_url}")

    plugin_instance = plugin_class(session)
    try:
        import_results = plugin_instance.validate_and_import_url(stripped_url)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for import_result in import_results:
        old_link_title_to_tmdb(
            session,
            import_result.title,
            tmdb_title,
            "Automatic: Import match",
        )

    session.flush()
    session.expire(tmdb_title, ["linked_title_links"])
    imported_title_keys = {import_result.title.key for import_result in import_results}
    for linked_title_link in tmdb_title.linked_title_links:
        linked_title = linked_title_link.linked_title
        if linked_title.key not in imported_title_keys:
            continue
        linked_title.tmdb_title_validated_at = tz_datetime.now()
        linked_title_link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        linked_title_link.manual_tmdb_link = True
        session.add(linked_title)
        session.add(linked_title_link)

    session.commit()
    session.refresh(tmdb_title)
    return tmdb_title


# TODO: Validate
def old_unlink_title_from_tmdb_title(
    session: Session,
    website_title: Title,
    tmdb_title: Title,
) -> Title:
    """Take `tmdb_title` off what `website_title` stands for.

    Episodes matched against it are unmatched, hand-settled or not, and the rest
    are matched again against the links that are left. The lock is left as it is.
    """
    for tmdb_title_link in list(website_title.tmdb_title_links):
        if tmdb_title_link.tmdb_title_id == tmdb_title.id:
            session.delete(tmdb_title_link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are settled against.
    session.expire(website_title, ["tmdb_title_links", "is_linked"])

    _old_unlink_episodes_from_dropped_tmdb_titles(session, website_title)
    _old_relink_episode(session, website_title)
    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def old_make_title_unlinked(session: Session, website_title: Title) -> Title:
    """Make `website_title` canonical again, dropping every TMDB link it has."""
    if not website_title.tmdb_title_links:
        message = "This title is already a canonical title."
        raise HTTPException(status_code=409, detail=message)

    _old_move_channel_titles_to_title(
        session,
        website_title,
        website_title.tmdb_title_ids,
    )

    for tmdb_title_link in list(website_title.tmdb_title_links):
        session.delete(tmdb_title_link)
    session.flush()
    session.expire(website_title, ["tmdb_title_links", "is_linked"])

    _old_unlink_episodes_from_dropped_tmdb_titles(session, website_title)
    website_title.tmdb_title_validated_at = tz_datetime.now()
    session.add(website_title)
    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def _old_move_channel_titles_to_title(
    session: Session,
    new_tmdb_title: Title,
    previous_tmdb_title_ids: list[uuid.UUID],
) -> None:
    """Move channel membership from the previous canonical titles onto the title."""
    channel_ids = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.tmdb_title_id == new_tmdb_title.id,
            ),
        ).all(),
    )
    previous_channel_titles = session.exec(
        select(ChannelTitle).where(
            col(ChannelTitle.tmdb_title_id).in_(previous_tmdb_title_ids),
        ),
    ).all()
    for channel_title in previous_channel_titles:
        if channel_title.channel_id in channel_ids:
            continue
        channel_ids.add(channel_title.channel_id)
        session.add(
            ChannelTitle(
                channel_id=channel_title.channel_id,
                tmdb_title_id=new_tmdb_title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


# TODO: Validate
def _old_unlink_episodes_from_dropped_tmdb_titles(
    session: Session,
    website_title: Title,
) -> None:
    episodes = _title_episodes(session, website_title)
    if not episodes:
        return

    tmdb_title_ids = {tmdb_title.id for tmdb_title in website_title.tmdb_titles}
    episode_ids = [episode.id for episode in episodes]
    kept_tmdb_episode_ids = (
        select(col(Episode.id))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .where(col(Season.title_id).in_(tmdb_title_ids))
    )
    session.exec(
        delete(EpisodeTmdbEpisode)
        .where(
            col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
            col(EpisodeTmdbEpisode.tmdb_episode_id).not_in(kept_tmdb_episode_ids),
        )
        .execution_options(synchronize_session=False),
    )
    still_linked_episode_ids = set(
        session.exec(
            select(col(EpisodeTmdbEpisode.episode_id)).where(
                col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
            ),
        ).all(),
    )
    for episode in episodes:
        session.expire(episode, ["tmdb_episode_links", "is_linked"])
        if (
            episode.id not in still_linked_episode_ids
            and episode.tmdb_episode_validated_at is not None
        ):
            episode.tmdb_episode_validated_at = None
            session.add(episode)
    session.flush()


# TODO: Validate
def _hand_settled_tmdb_title_ids(session: Session, title: Title) -> set[uuid.UUID]:
    episode_ids = [episode.id for episode in _title_episodes(session, title)]
    if not episode_ids:
        return set()

    tmdb_episode = aliased(Episode)
    return set(
        session.exec(
            select(Season.title_id)
            .join(tmdb_episode, col(Season.id) == col(tmdb_episode.season_id))
            .join(
                EpisodeTmdbEpisode,
                col(tmdb_episode.id) == col(EpisodeTmdbEpisode.tmdb_episode_id),
            )
            .join(Episode, col(Episode.id) == col(EpisodeTmdbEpisode.episode_id))
            .where(
                col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
                or_(
                    col(EpisodeTmdbEpisode.manual_tmdb_link).is_(True),
                    col(Episode.tmdb_episode_validated_at).is_not(None),
                ),
            ),
        ).all(),
    )


# TODO: Validate
def relink_title(session: Session, title: Title) -> None:
    if title.tmdb_title_validated_at is not None:
        return

    matched_tmdb_titles = tmdb_titles_from_title(session, title)
    if not matched_tmdb_titles:
        return

    matched_ids = {tmdb_title.id for tmdb_title in matched_tmdb_titles}
    kept_ids = _hand_settled_tmdb_title_ids(session, title)
    for tmdb_title_link in list(title.tmdb_title_links):
        if tmdb_title_link.tmdb_title_id in matched_ids:
            continue
        if tmdb_title_link.manual_tmdb_link:
            continue
        if tmdb_title_link.tmdb_title_id in kept_ids:
            continue
        session.delete(tmdb_title_link)
    session.flush()
    session.expire(title, ["tmdb_title_links", "is_linked"])

    linked_ids = {link.tmdb_title_id for link in title.tmdb_title_links}
    for tmdb_title in matched_tmdb_titles:
        if tmdb_title.id in linked_ids:
            continue
        old_link_title_to_tmdb(
            session,
            title,
            tmdb_title,
            "Automatic: Found match on TMDB",
        )

    _old_unlink_episodes_from_dropped_tmdb_titles(session, title)
    _old_relink_episode(session, title)


# TODO: Validate
def automatically_linked_titles() -> SelectOfScalar[uuid.UUID]:
    any_link = select(TitleTmdbTitle.title_id).where(
        col(TitleTmdbTitle.title_id) == col(Title.id),
    )
    manual_link = any_link.where(col(TitleTmdbTitle.manual_tmdb_link).is_(True))
    hand_settled_episode = (
        select(col(EpisodeTmdbEpisode.episode_id))
        .join(Episode, col(Episode.id) == col(EpisodeTmdbEpisode.episode_id))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .where(
            col(Season.title_id) == col(Title.id),
            or_(
                col(EpisodeTmdbEpisode.manual_tmdb_link).is_(True),
                col(Episode.tmdb_episode_validated_at).is_not(None),
            ),
        )
    )
    return (
        select(col(Title.id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Title.deleted_at).is_(None),
            col(Title.tmdb_title_validated_at).is_(None),
            Plugin.key != TMDB_PLUGIN_KEY,
            any_link.exists(),
            ~manual_link.exists(),
            ~hand_settled_episode.exists(),
        )
    )


# TODO: Validate
def _move_channel_titles_off_dropped_links(
    session: Session,
    title_ids: Sequence[uuid.UUID],
) -> None:
    rows = session.exec(
        select(ChannelTitle.channel_id, TitleTmdbTitle.title_id)
        .join(
            TitleTmdbTitle,
            col(TitleTmdbTitle.tmdb_title_id) == col(ChannelTitle.tmdb_title_id),
        )
        .where(col(TitleTmdbTitle.title_id).in_(title_ids)),
    ).all()
    if not rows:
        return

    existing = set(
        session.exec(
            select(ChannelTitle.channel_id, ChannelTitle.tmdb_title_id).where(
                col(ChannelTitle.tmdb_title_id).in_({title_id for _, title_id in rows}),
            ),
        ).all(),
    )
    for channel_id, title_id in dict.fromkeys(rows):
        if (channel_id, title_id) in existing:
            continue
        existing.add((channel_id, title_id))
        session.add(
            ChannelTitle(
                channel_id=channel_id,
                tmdb_title_id=title_id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


# TODO: Validate
def _unlink_episodes_of_titles(
    session: Session,
    title_ids: Sequence[uuid.UUID],
) -> None:
    episode_ids = (
        select(col(Episode.id))
        .join(Season, col(Season.id) == col(Episode.season_id))
        .where(col(Season.title_id).in_(title_ids))
    )
    verified_episode_ids = select(col(Episode.id)).where(
        col(Episode.id).in_(episode_ids),
        col(Episode.tmdb_episode_validated_at).is_not(None),
    )
    session.exec(
        delete(EpisodeTmdbEpisode)
        .where(
            col(EpisodeTmdbEpisode.episode_id).in_(episode_ids),
            col(EpisodeTmdbEpisode.manual_tmdb_link).is_(False),
            col(EpisodeTmdbEpisode.episode_id).not_in(verified_episode_ids),
        )
        .execution_options(synchronize_session=False),
    )


# TODO: Validate
def reset_automatic_title_links(
    session: Session,
    title_ids: Sequence[uuid.UUID],
) -> int:
    """Drop every automatic link these titles hold so they are linked again."""
    if not title_ids:
        return 0

    _move_channel_titles_off_dropped_links(session, title_ids)
    _unlink_episodes_of_titles(session, title_ids)
    session.exec(
        delete(TitleTmdbTitle)
        .where(col(TitleTmdbTitle.title_id).in_(title_ids))
        .execution_options(synchronize_session=False),
    )
    session.exec(
        update(Title)
        .where(col(Title.id).in_(title_ids))
        .values(link_status=None)
        .execution_options(synchronize_session=False),
    )
    session.commit()
    return len(title_ids)


# TODO: Validate
def automatic_link_groups(
    session: Session,
    *,
    by_source: bool,
) -> list[AutomaticLinkGroupOutput]:
    """Count the titles waiting to be linked again, per plugin or per source."""
    grouped_id = col(Source.id) if by_source else col(Plugin.id)
    grouped_key = col(Source.key) if by_source else col(Plugin.key)
    rows = session.exec(
        select(
            grouped_id,
            grouped_key,
            col(Plugin.key),
            func.count(col(Title.id)),
        )
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(col(Title.id).in_(automatically_linked_titles()))
        .group_by(grouped_id, grouped_key, col(Plugin.key))
        .order_by(func.count(col(Title.id)).desc()),
    ).all()
    return [
        AutomaticLinkGroupOutput(
            id=group_id,
            key=group_key,
            plugin_key=plugin_key,
            title_count=title_count,
        )
        for group_id, group_key, plugin_key, title_count in rows
    ]


# TODO: Validate
def reset_automatic_link_group(
    session: Session,
    group_id: uuid.UUID,
    *,
    by_source: bool,
) -> Message:
    """Drop the automatic links of every title in one plugin or source."""
    grouped_id = col(Source.id) if by_source else col(Plugin.id)
    title_ids = session.exec(
        select(col(Title.id))
        .join(Source, col(Source.id) == col(Title.source_id))
        .join(Plugin, col(Plugin.id) == col(Source.plugin_id))
        .where(
            col(Title.id).in_(automatically_linked_titles()),
            grouped_id == group_id,
        ),
    ).all()
    reset_automatic_title_links(session, title_ids)
    return Message(message=f"Reset {len(title_ids)} titles")
