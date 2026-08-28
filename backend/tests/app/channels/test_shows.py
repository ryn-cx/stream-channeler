# TODO: Validate
"""What the channel service says a channel's show list holds."""

import pytest
from sqlmodel import Session

from app.channels import service
from tests.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.app.helpers.utils import random_lower_string
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import create_random_user


# TODO: Validate
@pytest.mark.parametrize("show_count", [0, 1, 2])
def test_a_channel_lists_every_show_on_it(
    session_scoped_session: Session,
    show_count: int,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    expected_ids = set()
    for _ in range(show_count):
        channel_show = create_random_channel_show(session_scoped_session, channel)
        show = channel_show_show(session_scoped_session, channel_show)
        expected_ids.add(show.id)

    output = service.channel_shows_output(channel, owner, session_scoped_session)

    assert {show.id for show in output.shows} == expected_ids


# TODO: Validate
def test_a_shows_source_comes_back_with_it(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)
    show = channel_show_show(session_scoped_session, channel_show)

    output = service.channel_shows_output(channel, owner, session_scoped_session)

    assert show.source_id in output.sources


# TODO: Validate
def test_a_filter_only_show_is_listed_apart(session_scoped_session: Session) -> None:
    """A show on a channel only to hide episodes is not one the channel offers."""
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    filter_only = create_random_channel_show(
        session_scoped_session,
        channel,
        is_blacklist_only=True,
    )
    hidden_show = channel_show_show(session_scoped_session, filter_only)

    output = service.channel_shows_output(channel, owner, session_scoped_session)

    assert hidden_show.id not in {show.id for show in output.shows}
    assert hidden_show.id in {show.id for show in output.filter_only_shows}


# TODO: Validate
def test_removing_a_show_takes_it_off_the_channel(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_show = create_random_channel_show(session_scoped_session, channel)

    service.remove_show(session_scoped_session, channel_show)

    output = service.channel_shows_output(channel, owner, session_scoped_session)
    assert output.shows == []


# TODO: Validate
def test_removing_a_show_names_it_in_the_answer(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    name = random_lower_string()
    show = create_random_show(session_scoped_session, name=name)
    channel_show = create_random_channel_show(session_scoped_session, channel, show)

    message = service.remove_show(session_scoped_session, channel_show)

    assert name in message.message


# TODO: Validate
def test_adding_a_show_puts_it_on_the_channel(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    show = create_random_show(session_scoped_session)

    service.add_show(session_scoped_session, channel, show)

    output = service.channel_shows_output(channel, owner, session_scoped_session)
    assert show.id in {listed.id for listed in output.shows}


# TODO: Validate
def test_adding_a_show_twice_leaves_one_entry(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    show = create_random_show(session_scoped_session)

    service.add_show(session_scoped_session, channel, show)
    service.add_show(session_scoped_session, channel, show)

    output = service.channel_shows_output(channel, owner, session_scoped_session)
    assert len(output.shows) == 1
