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

from app.canonical_media.filters import is_canonical
from app.channels.models import ChannelTitle
from app.episodes.linking import EpisodeLinker
from app.episodes.models import MANUAL_NOTE_PREFIX, Episode, EpisodeCanonicalEpisode
from app.episodes.preload import preload_episodes
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.titles.models import Title, TitleCanonicalTitle
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import MediaNotFoundError

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import TMDBLookupInfo

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def _reread_in_new_order(session: Session, title: Title) -> None:
    """Read `title` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    logger.info(f"Rereading title in a new order: {title.name or title.key}")
    TMDB(session).update_title(title, force=True)


# TODO: Validate
def _relinkable_episodes(session: Session, title: Title) -> list[Episode]:
    preload_episodes(session, [title])
    return [
        episode
        for season in title.active_children
        for episode in season.active_children
        if episode.canonical_episode_validated_at is None
    ]


# TODO: Validate
def _preload_canonical_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> None:
    unread = [
        episode.id
        for episode in episodes
        if "canonical_episode_links" in instance_state(episode).unloaded
    ]
    if not unread:
        return
    session.exec(
        select(Episode)
        .where(col(Episode.id).in_(unread))
        .options(
            selectinload(Episode.canonical_episode_links).selectinload(  # type: ignore[arg-type]
                EpisodeCanonicalEpisode.canonical_episode,  # type: ignore[arg-type]
            ),
        ),
    ).all()


# TODO: Validate
def _clear_canonical_episode_links(
    session: Session,
    episodes: Sequence[Episode],
) -> None:
    _preload_canonical_episode_links(session, episodes)
    links = [link for episode in episodes for link in episode.canonical_episode_links]
    if not links:
        return

    session.exec(
        delete(EpisodeCanonicalEpisode).where(
            col(EpisodeCanonicalEpisode.episode_id).in_(
                [episode.id for episode in episodes],
            ),
        ),
    )
    for link in links:
        if link in session:
            session.expunge(link)
    for episode in episodes:
        set_committed_value(episode, "canonical_episode_links", [])


# TODO: Validate
def _relink_non_canonical_titles(session: Session, canonical_title: Title) -> None:
    """Match every non-canonical row of `canonical_title` against it again."""
    for link in list(canonical_title.non_canonical_title_links):
        _relink_non_canonical_title(session, link.non_canonical_title)


# TODO: Validate
def _relink_non_canonical_title(
    session: Session,
    non_canonical_title: Title,
) -> None:
    _clear_canonical_episode_links(
        session,
        _relinkable_episodes(session, non_canonical_title),
    )
    linker = EpisodeLinker(session, non_canonical_title)
    with session.no_autoflush:
        linker.link_title()


# TODO: Validate
def relink_title(session: Session, title: Title) -> Title:
    if title.is_canonical:
        _relink_non_canonical_titles(session, title)
    else:
        _relink_non_canonical_title(session, title)
    session.commit()
    session.refresh(title)
    return title


# TODO: Validate
def _validate_titles(title: Title, tmdb_title: Title) -> None:
    """Validate that `title` and `tmdb_title` can be linked.

    The title cannot have any other canonical titles linked to it and it cannot be a TMDB
    title.

    The TMDB title must be canonical TMDB title."""
    if not tmdb_title.is_canonical:
        message = f"{tmdb_title} is not a canonical title."
        raise ValueError(message)
    if tmdb_title.source.plugin.key != TMDB_PLUGIN_KEY:
        message = f"{tmdb_title} is not a TMDB title."
        raise ValueError(message)
    if title.source.plugin.key == TMDB_PLUGIN_KEY:
        message = f"{title} is a TMDB title."
        raise ValueError(message)
    if title.non_canonical_title_links:
        message = f"{title} has other titles linked to it."
        raise ValueError(message)


# TODO: Validate
def link_title_to_tmdb(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleCanonicalTitle:
    """Link a title to TMDB then links the title's episodes to TMDB.

    Will not remove any existing title links.
    Will relink existing titles to try to find better matches."""
    _validate_titles(title, tmdb_title)
    link: TitleCanonicalTitle
    if title.is_canonical:
        link = _link_canonical_title(session, title, tmdb_title, note)
    else:
        link = _link_non_canonical_title(title, tmdb_title, note)

    session.add(link)
    session.flush()
    session.expire(title, ["canonical_title_links", "is_canonical"])
    _relink_non_canonical_title(session, title)
    return link


# TODO: Validate
def _link_non_canonical_title(
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleCanonicalTitle:
    # If the link already exists nothing needs to be done.
    for tmdb_link in title.canonical_title_links:
        if tmdb_link.canonical_title_id == tmdb_title.id:
            return tmdb_link

    return TitleCanonicalTitle(
        title_id=title.id,
        canonical_title_id=tmdb_title.id,
        note=note,
    )


# TODO: Validate
def _link_canonical_title(
    session: Session,
    title: Title,
    tmdb_title: Title,
    note: str,
) -> TitleCanonicalTitle:
    _update_channels(session, title, tmdb_title)

    return TitleCanonicalTitle(
        title_id=title.id,
        canonical_title_id=tmdb_title.id,
        note=note,
    )


# TODO: Validate
def _update_channels(
    session: Session,
    title: Title,
    canonical_title: Title,
) -> None:
    """Update channels to replace the original canonical title with the TMDB title."""
    channels_with_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.canonical_title_id == title.id,
            ),
        ).all(),
    )
    if not channels_with_title:
        return

    channels_with_title_and_tmdb_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.canonical_title_id == canonical_title.id,
                col(ChannelTitle.channel_id).in_(channels_with_title),
            ),
        ).all(),
    )
    for channel_id in channels_with_title - channels_with_title_and_tmdb_title:
        session.add(
            ChannelTitle(
                channel_id=channel_id,
                canonical_title_id=canonical_title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


# TODO: Validate
def link_plugin_title_to_tmdb(
    session: Session,
    unlinked_title: Title,
    lookup_infos: Sequence[TMDBLookupInfo],
) -> None:
    """Link a plugin's title to TMDB using tmdb_lookup_info."""
    tmdb_titles = _find_tmdb_titles(session, lookup_infos)
    for tmdb_title in tmdb_titles:
        note = "Automatic: Found match on TMDB"
        link_title_to_tmdb(session, unlinked_title, tmdb_title, note)


# TODO: Validate
def _find_tmdb_titles(
    session: Session,
    lookup_infos: Sequence[TMDBLookupInfo],
) -> list[Title]:
    from plugins.TMDB import TMDB  # noqa: PLC0415

    tmdb_plugin = TMDB(session)
    tmdb_titles: list[Title] = []
    for lookup_info in lookup_infos:
        try:
            search_results = tmdb_plugin.import_search(
                [lookup_info.name],
                lookup_info.media_type,
                lookup_info.year,
            )
        except MediaNotFoundError:
            continue
        tmdb_title = next(
            (search_result.title for search_result in search_results),
            None,
        )
        if tmdb_title and tmdb_title not in tmdb_titles:
            tmdb_titles.append(tmdb_title)
    return tmdb_titles


# TODO: Validate
def link_title_to_canonical_title(
    session: Session,
    website_title: Title,
    canonical_title: Title,
) -> Title:
    """Add an admin's chosen `canonical_title` to what `website_title` stands for.

    Added alongside any existing links rather than replacing them, since one page
    can hold several titles. Removing one is `unlink_title_from_canonical_title`.
    The choice is locked so the next import cannot overrule it.
    """
    if website_title.non_canonical_title_links:
        message = "A title other titles are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )

    link_title_to_tmdb(
        session,
        website_title,
        canonical_title,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    remove_plugin_unmatched_sources(
        session,
        canonical_title.id,
        website_title.source.plugin.key,
    )
    website_title.canonical_title_validated_at = tz_datetime.now()
    session.add(website_title)

    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def link_title_to_canonical_title_from_tmdb_url(
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

    imported_titles = TMDB(session).import_url(stripped_url)
    canonical_title = session.exec(
        select(Title).where(
            is_canonical(Title),
            Title.key == imported_titles[0].title.key,
        ),
    ).one()
    return link_title_to_canonical_title(session, website_title, canonical_title)


# TODO: Validate
def import_non_canonical_title_from_url(
    session: Session,
    canonical_title: Title,
    title_url: str,
) -> Title:
    """Import the title at `title_url` and link it to `canonical_title`."""
    from app.sources.service.unmatched import (  # noqa: PLC0415
        remove_plugin_unmatched_sources,
    )
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import get_plugin_for_url  # noqa: PLC0415

    stripped_url = title_url.strip()
    if not canonical_title.is_canonical:
        message = "A title linked to a canonical title cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = get_plugin_for_url(stripped_url)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {stripped_url}")

    plugin_instance = plugin_class(session)
    try:
        import_results = plugin_instance.import_url(stripped_url)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    for import_result in import_results:
        link_title_to_tmdb(
            session,
            import_result.title,
            canonical_title,
            "Automatic: Import match",
        )

    remove_plugin_unmatched_sources(
        session,
        canonical_title.id,
        plugin_class.plugin_name(),
    )
    session.flush()
    session.expire(canonical_title, ["non_canonical_title_links"])
    imported_title_keys = {import_result.title.key for import_result in import_results}
    for non_canonical_title_link in canonical_title.non_canonical_title_links:
        non_canonical_title = non_canonical_title_link.non_canonical_title
        if non_canonical_title.key not in imported_title_keys:
            continue
        non_canonical_title.canonical_title_validated_at = tz_datetime.now()
        non_canonical_title_link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        session.add(non_canonical_title)
        session.add(non_canonical_title_link)

    session.commit()
    session.refresh(canonical_title)
    return canonical_title


# TODO: Validate
def unlink_title_from_canonical_title(
    session: Session,
    website_title: Title,
    canonical_title: Title,
) -> Title:
    """Take `canonical_title` off what `website_title` stands for.

    Episodes matched against it are unmatched, hand-settled or not, and the rest
    are matched again against the links that are left. The lock is left as it is.
    """
    for canonical_title_link in list(website_title.canonical_title_links):
        if canonical_title_link.canonical_title_id == canonical_title.id:
            session.delete(canonical_title_link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are settled against.
    session.expire(website_title, ["canonical_title_links", "is_canonical"])

    _unlink_episodes_from_dropped_canonical_titles(session, website_title)
    _relink_non_canonical_title(session, website_title)
    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def make_title_canonical(session: Session, website_title: Title) -> Title:
    """Make `website_title` canonical again, dropping every TMDB link it has."""
    if not website_title.canonical_title_links:
        message = "This title is already a canonical title."
        raise HTTPException(status_code=409, detail=message)

    _move_channel_titles_to_title(
        session,
        website_title,
        website_title.canonical_title_ids,
    )

    for canonical_title_link in list(website_title.canonical_title_links):
        session.delete(canonical_title_link)
    session.flush()
    session.expire(website_title, ["canonical_title_links", "is_canonical"])

    _unlink_episodes_from_dropped_canonical_titles(session, website_title)
    website_title.canonical_title_validated_at = tz_datetime.now()
    session.add(website_title)
    session.commit()
    session.refresh(website_title)
    return website_title


# TODO: Validate
def _move_channel_titles_to_title(
    session: Session,
    new_canonical_title: Title,
    previous_canonical_title_ids: list[uuid.UUID],
) -> None:
    """Move channel membership from the previous canonical titles onto the title."""
    channel_ids = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                ChannelTitle.canonical_title_id == new_canonical_title.id,
            ),
        ).all(),
    )
    previous_channel_titles = session.exec(
        select(ChannelTitle).where(
            col(ChannelTitle.canonical_title_id).in_(previous_canonical_title_ids),
        ),
    ).all()
    for channel_title in previous_channel_titles:
        if channel_title.channel_id in channel_ids:
            continue
        channel_ids.add(channel_title.channel_id)
        session.add(
            ChannelTitle(
                channel_id=channel_title.channel_id,
                canonical_title_id=new_canonical_title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


# TODO: Validate
def _unlink_episodes_from_dropped_canonical_titles(
    session: Session,
    website_title: Title,
) -> None:
    """Take every episode of `website_title` off a record no linked title holds."""
    canonical_title_ids = {
        canonical_title.id for canonical_title in website_title.canonical_titles
    }
    for season in website_title.active_children:
        for episode in season.active_children:
            for canonical_episode_link in list(episode.canonical_episode_links):
                canonical_episode = canonical_episode_link.canonical_episode
                if canonical_episode.season.title_id in canonical_title_ids:
                    continue
                session.delete(canonical_episode_link)
            session.flush()
            session.expire(episode, ["canonical_episode_links", "is_canonical"])

            if not episode.canonical_episode_links:
                episode.canonical_episode_validated_at = None
                session.add(episode)
    session.flush()
