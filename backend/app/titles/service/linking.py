# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

import re
import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import instance_state, set_committed_value
from sqlmodel import Session, col, delete, select

from app.channels.models import ChannelTitle
from app.episodes.linking import EpisodeLinkerV2
from app.episodes.models import (
    MANUAL_NOTE_PREFIX,
    Episode,
    EpisodeTmdbEpisode,
    is_manual_note,
)
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle
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
    _old_clear_tmdb_episode_links(
        session,
        _old_relinkable_episodes(session, linked_title),
    )
    linker = EpisodeLinkerV2(session, linked_title)
    with session.no_autoflush:
        linker.link_titles()


# TODO: Validate
def _old_relinkable_episodes(session: Session, title: Title) -> list[Episode]:
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
        if episode.tmdb_episode_validated_at is None
    ]


# TODO: Validate
def _old_clear_tmdb_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> None:
    _old_preload_tmdb_episode_links(session, episodes)
    # A link a `User` settled themselves is left where it is, so what is cleared
    # is only ever a guess an automatic match made.
    kept_links = {
        episode.id: [
            link for link in episode.tmdb_episode_links if link.manual_tmdb_link
        ]
        for episode in episodes
    }
    dropped_links = [
        link
        for episode in episodes
        for link in episode.tmdb_episode_links
        if not link.manual_tmdb_link
    ]
    if not dropped_links:
        return

    session.exec(
        delete(EpisodeTmdbEpisode).where(
            col(EpisodeTmdbEpisode.episode_id).in_(
                [episode.id for episode in episodes],
            ),
            col(EpisodeTmdbEpisode.manual_tmdb_link).is_(False),
        ),
    )
    for link in dropped_links:
        if link in session:
            session.expunge(link)
    for episode in episodes:
        set_committed_value(
            episode,
            "tmdb_episode_links",
            kept_links[episode.id],
        )


# TODO: Validate
def _old_reread_in_new_order(session: Session, title: Title) -> None:
    """Read `title` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    logger.info(f"Rereading title in a new order: {title.name or title.key}")
    TMDB(session).update_title(title, force=True)


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
def _old_link_linked_title(
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleTmdbTitle:
    # If the link already exists nothing needs to be done.
    for tmdb_link in title.tmdb_title_links:
        if tmdb_link.tmdb_title_id == tmdb_title.id:
            return tmdb_link

    return TitleTmdbTitle(
        title_id=title.id,
        tmdb_title_id=tmdb_title.id,
        note=note,
        manual_tmdb_link=is_manual_note(note),
    )


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

    Will not remove any existing title links.
    Will relink existing titles to try to find better matches."""
    _old_validate_titles(title, tmdb_title)
    if not title.is_linked:
        return link_unlinked_title_to_tmdb(session, title, tmdb_title, note)

    link = _old_link_linked_title(title, tmdb_title, note)
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
    """Add an admin's chosen `tmdb_title` to what `website_title` stands for.

    Added alongside any existing links rather than replacing them, since one page
    can hold several titles. Removing one is `old_unlink_title_from_tmdb_title`.
    The choice is locked so the next import cannot overrule it.
    """
    if website_title.linked_title_links:
        message = "A title other titles are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )

    old_link_title_to_tmdb(
        session,
        website_title,
        tmdb_title,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    remove_plugin_unmatched_sources(
        session,
        tmdb_title.id,
        website_title.source.plugin.key,
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
    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )
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

    remove_plugin_unmatched_sources(
        session,
        tmdb_title.id,
        plugin_class.plugin_name(),
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
    """Take every episode of `website_title` off a record no linked title holds."""
    tmdb_title_ids = {tmdb_title.id for tmdb_title in website_title.tmdb_titles}
    for season in website_title.active_children:
        for episode in season.active_children:
            for tmdb_episode_link in list(episode.tmdb_episode_links):
                tmdb_episode = tmdb_episode_link.tmdb_episode
                if tmdb_episode.season.title_id in tmdb_title_ids:
                    continue
                session.delete(tmdb_episode_link)
            session.flush()
            session.expire(episode, ["tmdb_episode_links", "is_linked"])

            if not episode.tmdb_episode_links:
                episode.tmdb_episode_validated_at = None
                session.add(episode)
    session.flush()
