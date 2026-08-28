# TODO: Validate
"""What the channel service says about a title's filters on a channel.

A filter is about the media rather than one website's row of it, so what is read
back is the title's own seasons and episodes, with each site listed beside them.
"""

import pytest
from sqlmodel import Session

from app.channels import service
from app.channels.schemas import WhitelistEntryInput, WhitelistShowInput
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.episodes.utils import create_random_episode
from tests.app.seasons.utils import create_random_season
from tests.app.users.utils import create_random_user


# TODO: Validate
def test_a_titles_sites_are_listed(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)
    show = channel_show_show(session_scoped_session, channel_show)

    output = service.channel_whitelist_output(session_scoped_session, channel_show)

    assert {source.show_id for source in output.sources} == {show.id}


# TODO: Validate
@pytest.mark.parametrize("season_count", [0, 1, 2])
def test_every_season_of_the_title_is_listed(
    session_scoped_session: Session,
    season_count: int,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)
    show = channel_show_show(session_scoped_session, channel_show)
    season_ids = {
        create_random_season(session_scoped_session, show).id
        for _ in range(season_count)
    }

    output = service.channel_whitelist_output(session_scoped_session, channel_show)

    assert {season.id for season in output.seasons} == season_ids


# TODO: Validate
def test_nothing_is_filtered_before_anything_is_chosen(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)
    show = channel_show_show(session_scoped_session, channel_show)
    create_random_season(session_scoped_session, show)

    output = service.channel_whitelist_output(session_scoped_session, channel_show)

    assert [season for season in output.seasons if season.filtered] == []
    assert [source for source in output.sources if source.filtered] == []


# TODO: Validate
def test_marking_a_season_records_it(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(
        session_scoped_session,
        channel,
        is_whitelist=True,
    )
    show = channel_show_show(session_scoped_session, channel_show)
    season = create_random_season(session_scoped_session, show)

    output = service.update_whitelist_output(
        session_scoped_session,
        WhitelistShowInput(
            is_whitelist=True,
            seasons=[WhitelistEntryInput(id=season.id, marked=True)],
        ),
        channel_show,
    )

    assert {s.id for s in output.seasons if s.filtered} == {season.id}


# TODO: Validate
def test_unmarking_a_season_forgets_it(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(
        session_scoped_session,
        channel,
        is_whitelist=True,
    )
    show = channel_show_show(session_scoped_session, channel_show)
    season = create_random_season(session_scoped_session, show)

    service.update_whitelist_output(
        session_scoped_session,
        WhitelistShowInput(
            is_whitelist=True,
            seasons=[WhitelistEntryInput(id=season.id, marked=True)],
        ),
        channel_show,
    )
    output = service.update_whitelist_output(
        session_scoped_session,
        WhitelistShowInput(
            is_whitelist=True,
            seasons=[WhitelistEntryInput(id=season.id, marked=False)],
        ),
        channel_show,
    )

    assert [s for s in output.seasons if s.filtered] == []


# TODO: Validate
def test_switching_between_whitelist_and_blacklist_is_recorded(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(
        session_scoped_session,
        channel,
        is_whitelist=True,
    )

    output = service.update_whitelist_output(
        session_scoped_session,
        WhitelistShowInput(is_whitelist=False),
        channel_show,
    )

    assert output.is_whitelist is False


# TODO: Validate
def test_a_seasons_episodes_are_read_a_page_at_a_time(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)
    show = channel_show_show(session_scoped_session, channel_show)
    season = create_random_season(session_scoped_session, show)
    for _ in range(3):
        create_random_episode(session_scoped_session, season)

    page = service.channel_whitelist_episodes_output(
        session_scoped_session,
        channel_show,
        season.id,
        offset=0,
        limit=2,
    )

    assert len(page.episodes) == 2  # noqa: PLR2004 - The number is the point of the test.
    assert page.total_count == 3  # noqa: PLR2004 - The number is the point of the test.


# TODO: Validate
def test_the_filtered_episodes_are_the_ones_marked(
    session_scoped_session: Session,
) -> None:
    """The blacklist reads back as the episodes it names, not the whole title."""
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(
        session_scoped_session,
        channel,
        is_whitelist=False,
    )
    show = channel_show_show(session_scoped_session, channel_show)
    season = create_random_season(session_scoped_session, show)
    marked = create_random_episode(session_scoped_session, season)
    create_random_episode(session_scoped_session, season)

    service.update_whitelist_output(
        session_scoped_session,
        WhitelistShowInput(
            is_whitelist=False,
            episodes=[WhitelistEntryInput(id=marked.id, marked=True)],
        ),
        channel_show,
    )
    filtered = service.filtered_whitelist_episodes(session_scoped_session, channel_show)

    assert {episode.canonical_episode_id for episode in filtered} == {marked.id}


# TODO: Validate
def test_nothing_is_filtered_when_nothing_was_marked(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)

    assert (
        service.filtered_whitelist_episodes(
            session_scoped_session,
            channel_show,
        )
        == []
    )
