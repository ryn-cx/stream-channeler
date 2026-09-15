# TODO: Validate

import pytest
from sqlmodel import Session

from app.channels.service import titles
from tests.app.channels.utils import (
    channel_title_title,
    create_random_channel,
    create_random_channel_title,
)
from tests.app.helpers.utils import random_lower_string
from tests.app.titles.utils import create_random_title
from tests.app.users.utils import create_random_user


# TODO: Validate
@pytest.mark.parametrize("title_count", [0, 1, 2])
def test_a_channel_lists_every_title_on_it(
    session_scoped_session: Session,
    title_count: int,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    expected_ids = set()
    for _ in range(title_count):
        channel_title = create_random_channel_title(session_scoped_session, channel)
        title = channel_title_title(session_scoped_session, channel_title)
        expected_ids.add(title.id)

    output = titles.channel_titles_output(channel, owner, session_scoped_session)

    assert {title.id for title in output.titles} == expected_ids


# TODO: Validate
def test_a_titles_source_comes_back_with_it(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_title = create_random_channel_title(session_scoped_session, channel)
    title = channel_title_title(session_scoped_session, channel_title)

    output = titles.channel_titles_output(channel, owner, session_scoped_session)

    assert title.source_id in output.sources


# TODO: Validate
def test_a_filter_only_title_is_listed_apart(session_scoped_session: Session) -> None:
    """A title on a channel only to hide episodes is not one the channel offers."""
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    filter_only = create_random_channel_title(
        session_scoped_session,
        channel,
        is_blacklist_only=True,
    )
    hidden_title = channel_title_title(session_scoped_session, filter_only)

    output = titles.channel_titles_output(channel, owner, session_scoped_session)

    assert hidden_title.id not in {title.id for title in output.titles}
    assert hidden_title.id in {title.id for title in output.filter_only_titles}


# TODO: Validate
def test_removing_a_title_takes_it_off_the_channel(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    channel_title = create_random_channel_title(session_scoped_session, channel)

    titles.remove_title(session_scoped_session, channel_title)

    output = titles.channel_titles_output(channel, owner, session_scoped_session)
    assert output.titles == []


# TODO: Validate
def test_removing_a_title_names_it_in_the_answer(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    name = random_lower_string()
    title = create_random_title(session_scoped_session, name=name)
    channel_title = create_random_channel_title(session_scoped_session, channel, title)

    message = titles.remove_title(session_scoped_session, channel_title)

    assert name in message.message


# TODO: Validate
def test_adding_a_title_puts_it_on_the_channel(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    title = create_random_title(session_scoped_session)

    titles.add_title(session_scoped_session, channel, title)

    output = titles.channel_titles_output(channel, owner, session_scoped_session)
    assert title.id in {listed.id for listed in output.titles}


# TODO: Validate
def test_adding_a_title_twice_leaves_one_entry(session_scoped_session: Session) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner.id)
    title = create_random_title(session_scoped_session)

    titles.add_title(session_scoped_session, channel, title)
    titles.add_title(session_scoped_session, channel, title)

    output = titles.channel_titles_output(channel, owner, session_scoped_session)
    assert len(output.titles) == 1
