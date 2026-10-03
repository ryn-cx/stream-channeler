# TODO: Validate

import uuid
from collections.abc import Sequence

from sqlmodel import Session, col, select

from app.channels.models import ChannelTitle
from app.titles.models import Title


# TODO: Validate
def _move_imported_channel_titles(
    session: Session,
    imported_title: Title,
    dropped_tmdb_title_ids: Sequence[uuid.UUID],
) -> None:
    """Bring the rows that were imported as `imported_title` back onto it.

    A row a `User` got by importing this title followed it onto whatever it was
    linked to. The link is going, so the row comes back to the title itself and
    the row it was standing as is dropped, which is what keeps a title linked to
    the wrong canonical title in the channel it was imported into.
    """
    if not dropped_tmdb_title_ids:
        return

    moved_channel_titles = session.exec(
        select(ChannelTitle).where(
            col(ChannelTitle.tmdb_title_id).in_(dropped_tmdb_title_ids),
            col(ChannelTitle.imported_title_id) == imported_title.id,
        ),
    ).all()
    if not moved_channel_titles:
        return

    channels_with_title = set(
        session.exec(
            select(ChannelTitle.channel_id).where(
                col(ChannelTitle.tmdb_title_id) == imported_title.id,
            ),
        ).all(),
    )
    for channel_title in moved_channel_titles:
        if channel_title.channel_id not in channels_with_title:
            channels_with_title.add(channel_title.channel_id)
            session.add(
                ChannelTitle(
                    channel_id=channel_title.channel_id,
                    tmdb_title_id=imported_title.id,
                    imported_title_id=imported_title.id,
                    is_whitelist=channel_title.is_whitelist,
                    is_blacklist_only=channel_title.is_blacklist_only,
                ),
            )
        session.delete(channel_title)
    session.flush()


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
                imported_title_id=new_tmdb_title.id,
                is_whitelist=False,
                is_blacklist_only=False,
            ),
        )
    session.flush()
