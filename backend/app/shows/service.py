# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

import re
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.canonical_media.filters import is_canonical
from app.canonical_media.keys import SHOW_LEVEL, tmdb_id_of
from app.canonical_media.metadata import canonical_show_of
from app.canonical_media.service import add_canonical_show
from app.channels.models import ChannelShow
from app.episodes.linking import EpisodeLinker
from app.episodes.models import MANUAL_NOTE_PREFIX, Episode
from app.issue_reports.service import list_show_issue_reports
from app.media.media_type import MediaType
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.seasons.models import Season
from app.shows.models import Show
from app.shows.schemas import (
    ShowInformationOutput,
    ShowInformationSide,
    ShowListPublic,
    ShowPublic,
    ShowUpdate,
    TmdbEpisodeGroupOption,
    UnvalidatedLinkedShowOutput,
    UnvalidatedShowOutput,
)
from app.sources.schemas import SourceListPublic
from app.users.models import User
from app.utils import tz_datetime

_TMDB_TITLE_URL = re.compile(r"themoviedb\.org/(?:movie|tv)/(?P<tmdb_id>\d+)")


# TODO: Validate
def add_canonical_show_and_link_episodes(
    session: Session,
    show: Show,
    canonical_show: Show | None = None,
) -> None:
    """Link `show` to the canonical show it is linked to, and read its episodes.

    A show TMDB has no match for is the canonical show, which is what it already is when
    it is written, so there is nothing to do for it here. One TMDB does have a match for
    is linked to that match, and `add_canonical_show` is what makes it non-canonical.

    A show already linked to a canonical show is left alone, since that may have
    been settled by hand and writing the show again is no reason to overrule it.
    A show linked to nothing is searched for afresh every time it is written,
    since a match that was not there to be found when it was first written can be
    there now.

    The episodes are read against the canonical show whether or not one was found
    here, because the episodes just written include ones the canonical show it is
    already linked to has never been read against.
    """
    if canonical_show:
        add_canonical_show(session, show, canonical_show)
    _relink_non_canonical_show(session, show)


# TODO: Validate
def set_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> Show:
    """Add the canonical show a `User` chose to what `show` already stands for.

    A website files two shows under one page often enough - a YouTube channel
    whose uploads are two series, a service selling a sequel as another season -
    that a title chosen by hand goes on beside whatever is already there rather
    than over it. Taking one off is `unset_canonical_show`, which is a thing to
    ask for rather than something choosing does quietly.

    The choice is locked, which is what stops the next import searching for a
    title of its own and overruling it. The episodes are read again afterwards,
    since the title just added holds episodes none of them has been read against.
    """
    if show.non_canonical_shows:
        message = "A show other shows are linked to cannot be linked to one itself."
        raise HTTPException(status_code=409, detail=message)

    add_canonical_show(
        session,
        show,
        canonical_show,
        note=f"{MANUAL_NOTE_PREFIX}Selection",
    )
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)

    _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def set_canonical_show_using_tmdb_url(
    session: Session,
    show: Show,
    url: str,
) -> Show:
    from plugins.TMDB import TMDB  # noqa: PLC0415

    address = url.strip()
    if not _TMDB_TITLE_URL.search(address):
        raise HTTPException(
            status_code=400,
            detail=f"{url} is not the address of a TMDB film or series",
        )

    imported = TMDB(session).import_url(address)
    canonical_show = session.exec(
        select(Show).where(is_canonical(Show), Show.key == imported[0].show_key),
    ).one()
    return set_canonical_show(session, show, canonical_show)


# TODO: Validate
def import_non_canonical_show_from_url(
    session: Session,
    canonical_show: Show,
    url: str,
) -> Show:
    from plugins.utils.abstract_plugin import InvalidURLError  # noqa: PLC0415
    from plugins.utils.manage_plugins import plugin_for_url  # noqa: PLC0415

    address = url.strip()
    if not canonical_show.is_canonical:
        message = "A show linked to a canonical show cannot hold rows of its own."
        raise HTTPException(status_code=409, detail=message)

    plugin_class = plugin_for_url(address)
    if plugin_class is None:
        raise HTTPException(status_code=400, detail=f"No plugin imports {address}")

    try:
        results = plugin_class(session).import_url(address, canonical_show)
    except InvalidURLError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    session.flush()
    session.expire(canonical_show, ["non_canonical_shows"])
    imported_keys = {result.show_key for result in results}
    for link in canonical_show.non_canonical_shows:
        if link.show.key not in imported_keys:
            continue
        link.show.canonical_show_validated_at = tz_datetime.now()
        link.note = f"{MANUAL_NOTE_PREFIX}Selection"
        session.add(link.show)
        session.add(link)
        _relink_non_canonical_show(session, link.show)

    session.commit()
    session.refresh(canonical_show)
    return canonical_show


# TODO: Validate
def unset_canonical_show(
    session: Session,
    show: Show,
    canonical_show: Show,
) -> Show:
    """Take `canonical_show` off what `show` stands for.

    Every episode that stood for an episode of the title being taken off is left
    standing for nothing, hand-settled or not: it was settled against a title
    this row has now been said not to be of. What the rest of the episodes are of
    is worked out afresh against the titles that are left.

    The lock stays as it was. An admin saying this row is not that title has
    settled something whether or not another title is named in its place, and an
    import searching for one afresh would only put the same guess back.
    """
    for link in list(show.canonical_show_links):
        if link.canonical_show_id == canonical_show.id:
            session.delete(link)
    session.flush()
    # Read again rather than left as it is, since a link deleted is still in the
    # collection it was read out of and what the row stands for now is what the
    # episodes below are settled against.
    session.expire(show, ["canonical_show_links", "is_canonical"])

    _unlink_unlisted_episodes(session, show)
    _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def canonicalize_show(session: Session, show: Show) -> Show:
    if not show.canonical_show_links:
        message = "This show is already a canonical show."
        raise HTTPException(status_code=409, detail=message)

    _add_channel_shows(session, show, show.canonical_show_ids)

    for link in list(show.canonical_show_links):
        session.delete(link)
    session.flush()
    session.expire(show, ["canonical_show_links", "is_canonical"])

    _unlink_unlisted_episodes(session, show)
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def _add_channel_shows(
    session: Session,
    show: Show,
    previous_canonical_show_ids: list[uuid.UUID],
) -> None:
    channel_ids = set(
        session.exec(
            select(ChannelShow.channel_id).where(
                ChannelShow.canonical_show_id == show.id,
            ),
        ).all(),
    )
    previous_channel_shows = session.exec(
        select(ChannelShow).where(
            col(ChannelShow.canonical_show_id).in_(previous_canonical_show_ids),
        ),
    ).all()
    for channel_show in previous_channel_shows:
        if channel_show.channel_id in channel_ids:
            continue
        channel_ids.add(channel_show.channel_id)
        session.add(
            ChannelShow(
                channel_id=channel_show.channel_id,
                canonical_show_id=show.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()


# TODO: Validate
def _unlink_unlisted_episodes(session: Session, show: Show) -> None:
    """Take every episode of `show` off a record no linked title holds."""
    canonical_show_ids = {linked.id for linked in show.canonical_shows}
    for season in show.active_children:
        for episode in season.active_children:
            for link in list(episode.canonical_episode_links):
                if link.canonical_episode.season.show_id in canonical_show_ids:
                    continue
                session.delete(link)
            session.flush()
            session.expire(episode, ["canonical_episode_links", "is_canonical"])

            if not episode.canonical_episode_links:
                episode.canonical_episode_validated_at = None
                episode.canonical_episode_note = None
                session.add(episode)
    session.flush()


# TODO: Validate
def list_tmdb_episode_groups(
    session: Session,
    show: Show,
) -> list[TmdbEpisodeGroupOption]:
    """Return the episode orders TMDB holds for `show`, for one to be chosen from.

    Its own endpoint rather than part of reading the show, because it is read off
    a downloaded file and only ever wanted by somebody about to choose an order.
    A row that is not a TMDB series has none, which reads as an empty list rather
    than as an error: there is nothing wrong with a title having no other order.
    """
    if show.source.plugin.key != TMDB_PLUGIN_KEY:
        return []

    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB import TMDB  # noqa: PLC0415
    from plugins.TMDB.keys import parse_show_key  # noqa: PLC0415

    media_type, tmdb_id = parse_show_key(show.key)
    if media_type is not MediaType.tv:
        return []

    groups_file = TMDB(session).episode_groups_file(tmdb_id)
    if not groups_file.database_record.content:
        return []

    return [
        TmdbEpisodeGroupOption(
            id=group.id,
            name=group.name,
            description=group.description,
            group_count=group.group_count,
            episode_count=group.episode_count,
            type=group.type,
        )
        for group in groups_file.parsed().results
    ]


# TODO: Validate
def update_show_extra(
    session: Session,
    show: Show,
    extra: dict[str, Any] | None,
) -> None:
    """Store `extra` on `show`, and read the title again where the order changed.

    The one way of setting what a plugin keeps about a title, so that whatever
    setting it has to drag along happens wherever it is set from.

    Changing the episode order is the case that drags something along. The order decides
    which season an episode sits in and what it is numbered, and a non-canonical row is
    matched to an episode by exactly those. The title is read again so the new order is
    written down.
    """
    validate_extra(session, show, extra)

    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB.episode_groups import chosen_group_id  # noqa: PLC0415

    reordered = chosen_group_id(show.extra) != chosen_group_id(extra)
    show.extra = extra or {}
    session.add(show)

    if reordered:
        _reread_in_new_order(session, show)
        _relink_non_canonical_shows(session, show)
    session.commit()


# TODO: Validate
def update_show_episode_group(
    session: Session,
    show: Show,
    group_id: str | None,
) -> None:
    """Read `show` in the episode order `group_id` names, or in its own for none."""
    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB.episode_groups import dump_extra  # noqa: PLC0415

    update_show_extra(session, show, dump_extra(group_id))


# TODO: Validate
def force_update_show(session: Session, show: Show) -> Show:
    from plugins.utils.manage_plugins import import_plugins, plugins  # noqa: PLC0415

    import_plugins()
    plugin_classes = {plugin.plugin_key(): plugin for plugin in plugins}
    plugin_class = plugin_classes.get(show.source.plugin.key)
    if plugin_class is None:
        message = f"No plugin named {show.source.plugin.key!r} to read the show again."
        raise HTTPException(status_code=422, detail=message)

    plugin_class(session).update_show(show, force=True)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def _reread_in_new_order(session: Session, show: Show) -> None:
    """Read `show` again so its seasons and numbering are the chosen order's."""
    # Imported here for the same reason as above.
    from plugins.TMDB import TMDB  # noqa: PLC0415

    TMDB(session).update_show(show, force=True)


# TODO: Validate
def _relink_non_canonical_shows(session: Session, canonical_show: Show) -> None:
    """Match every non-canonical row of `canonical_show` against it again."""
    for link in list(canonical_show.non_canonical_shows):
        _relink_non_canonical_show(session, link.show)


# TODO: Validate
def _relink_non_canonical_show(
    session: Session,
    non_canonical_show: Show,
) -> None:
    for season in non_canonical_show.active_children:
        for episode in season.active_children:
            if episode.canonical_episode_validated_at is not None:
                continue
            for episode_link in list(episode.canonical_episode_links):
                session.delete(episode_link)
            episode.canonical_episode_note = None
        session.flush()
        for episode in season.active_children:
            session.expire(episode, ["canonical_episode_links", "is_canonical"])
    EpisodeLinker(session, non_canonical_show).link_show()


# TODO: Validate
def relink_show(session: Session, show: Show) -> Show:
    if show.is_canonical:
        _relink_non_canonical_shows(session, show)
    else:
        _relink_non_canonical_show(session, show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def validate_extra(
    session: Session,
    show: Show,
    extra: dict[str, Any] | None,
) -> None:
    """Raise where `extra` names an episode order TMDB has no record of.

    Choosing an order replaces the title's own seasons with that order's groups,
    so an id naming nothing would leave the title with no seasons at all. The
    check is against the orders TMDB actually holds for this title rather than
    against the shape of the id, since an id that reads right and names another
    title's order is just as empty.

    Only TMDB's own rows carry an order, so a row of any other plugin is left
    alone: `extra` is each plugin's own scratch column and nothing here knows
    what another plugin keeps in it.
    """
    if show.source.plugin.key != TMDB_PLUGIN_KEY:
        return

    # Imported here rather than at the top of the module because the plugin is
    # built on the base every plugin is, which reads this module in turn.
    from plugins.TMDB import TMDB  # noqa: PLC0415
    from plugins.TMDB.episode_groups import chosen_group_id  # noqa: PLC0415
    from plugins.TMDB.keys import parse_show_key  # noqa: PLC0415

    group_id = chosen_group_id(extra)
    if group_id is None:
        return

    media_type, tmdb_id = parse_show_key(show.key)
    if media_type is not MediaType.tv:
        message = "A film has no episode orders to be read in."
        raise HTTPException(status_code=422, detail=message)

    groups_file = TMDB(session).episode_groups_file(tmdb_id)
    known = (
        {group.id for group in groups_file.parsed().results}
        if groups_file.database_record.content
        else set()
    )
    if group_id not in known:
        message = f"TMDB holds no episode order {group_id!r} for this show."
        raise HTTPException(status_code=422, detail=message)


# TODO: Validate
def validate_show(session: Session, show: Show) -> Show:
    """Settle the canonical shows a `Show` already stands for as the right ones.

    Nothing about what it stands for changes. A row linked to a title is being
    said to really be that title, and a row that is its own record is being said
    to be one TMDB holds no counterpart for, which is one decision about two
    answers and so one column either way.
    """
    show.canonical_show_validated_at = tz_datetime.now()
    session.add(show)
    session.commit()
    session.refresh(show)
    return show


# TODO: Validate
def list_unvalidated_shows(session: Session, limit: int) -> list[UnvalidatedShowOutput]:
    """Return every `Show` whose canonical shows no `User` has validated."""
    shows = session.exec(
        Show.select_with_plugin_eager()
        .where(
            col(Show.canonical_show_validated_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .order_by(col(Show.name))
        .limit(limit),
    ).all()

    show_ids = [show.id for show in shows]
    episode_counts = dict(
        session.exec(
            select(Season.show_id, func.count(col(Episode.id)))
            .join(Episode, onclause=col(Episode.season_id) == Season.id)
            .where(
                col(Season.show_id).in_(show_ids),
                col(Season.deleted_at).is_(None),
                col(Episode.deleted_at).is_(None),
            )
            .group_by(col(Season.show_id)),
        ).all(),
    )

    return [
        UnvalidatedShowOutput(
            **ShowListPublic.model_validate(show).model_dump(),
            episode_count=episode_counts.get(show.id, 0),
            created_at=show.created_at,
            linked_shows=[
                UnvalidatedLinkedShowOutput(
                    id=link.canonical_show.id,
                    name=link.canonical_show.name,
                    year=link.canonical_show.year,
                    url=link.canonical_show.url,
                    image_url=link.canonical_show.image_url,
                    tmdb_id=tmdb_id_of(link.canonical_show.key, SHOW_LEVEL),
                    note=link.note,
                )
                for link in show.canonical_show_links
            ],
        )
        for show in shows
    ]


# TODO: Validate
def _show_output(show: Show) -> ShowPublic:
    """Return a `Show` as the website that holds it stored it."""
    return ShowPublic.model_validate(show)


# TODO: Validate
def _information_side(label: str, show: Show) -> ShowInformationSide:
    return ShowInformationSide(
        label=label,
        show=ShowPublic.model_validate(show),
        source=SourceListPublic.model_validate(show.source),
    )


# TODO: Validate
def show_information(
    session: Session,
    show: Show,
    current_user: User | None,
) -> ShowInformationOutput:
    """Return what the website and TMDB each say about a `Show`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    source = show.source

    counterpart = canonical_show_of(session, show)
    tmdb: ShowInformationSide | None = None
    if counterpart:
        tmdb = _information_side(TMDB_PLUGIN_KEY, counterpart)

    return ShowInformationOutput(
        editable=current_user is not None and current_user.is_superuser,
        issue_reports=list_show_issue_reports(session, show.id),
        source=_information_side(
            source.name or source.plugin.name or source.plugin.key,
            show,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
def update_show_record(
    session: Session,
    show: Show,
    show_input: ShowUpdate,
) -> ShowPublic:
    """Write an update to a `Show`.

    Which canonical show this stands for is not something an update writes: it is
    linker's to work out during an import, or a `User`'s to settle through the
    TMDB matching screens, so there is nothing to repoint here.

    `extra` goes through its own service rather than being written with the rest, since
    what a TMDB row keeps there is the episode order the title is read in and changing
    that means reading the title again and matching every non-canonical row of it
    afresh.
    """
    # Before the rest of the update, because what it does depends on the order
    # the title is read in now and the general write would already have replaced
    # it. The same value going down twice writes nothing the second time.
    if "extra" in show_input.model_fields_set:
        update_show_extra(session, show, show_input.extra)
    return _show_output(show_input.update(session, show))
