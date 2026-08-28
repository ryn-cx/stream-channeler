# TODO: Validate
"""What the channel service does with a channel's import queue."""

import uuid

import pytest
from fastapi import HTTPException, status
from sqlmodel import Session

from app.channels import service
from app.channels.models import Channel, URLStatus
from tests.app.channels.utils import create_random_channel, create_random_channel_queue
from tests.app.helpers.utils import random_lower_string
from tests.app.users.utils import create_random_user


# TODO: Validate
def queued_urls(session: Session, channel: Channel) -> list[str]:
    return [entry.url for entry in service.channel_queue(session, channel)]


# TODO: Validate
def test_an_empty_queue_reads_as_nothing(session_scoped_session: Session) -> None:
    channel = create_random_channel(session_scoped_session)
    assert service.channel_queue(session_scoped_session, channel) == []


# TODO: Validate
def test_the_newest_url_is_read_first(session_scoped_session: Session) -> None:
    """New URLs go on top so they can be seen without scrolling to the bottom."""
    channel = create_random_channel(session_scoped_session)
    first = create_random_channel_queue(session_scoped_session, channel).url
    second = create_random_channel_queue(session_scoped_session, channel).url

    assert queued_urls(session_scoped_session, channel) == [second, first]


# TODO: Validate
@pytest.mark.parametrize("existing_count", [0, 1, 2])
@pytest.mark.parametrize("new_count", [0, 1, 2])
def test_adding_urls_keeps_the_ones_already_queued(
    session_scoped_session: Session,
    existing_count: int,
    new_count: int,
) -> None:
    channel = create_random_channel(session_scoped_session)
    existing = [
        create_random_channel_queue(session_scoped_session, channel).url
        for _ in range(existing_count)
    ]
    new = [random_lower_string() for _ in range(new_count)]

    service.add_queue_urls(session_scoped_session, channel, new)

    assert queued_urls(session_scoped_session, channel) == new[::-1] + existing[::-1]


# TODO: Validate
def test_a_url_already_queued_is_not_queued_twice(
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(session_scoped_session)
    existing = create_random_channel_queue(session_scoped_session, channel)

    service.add_queue_urls(session_scoped_session, channel, [existing.url])

    assert queued_urls(session_scoped_session, channel) == [existing.url]


# TODO: Validate
def test_the_same_url_given_twice_is_queued_once(
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(session_scoped_session)
    url = random_lower_string()

    service.add_queue_urls(session_scoped_session, channel, [url, url])

    assert queued_urls(session_scoped_session, channel) == [url]


# TODO: Validate
def test_deleting_a_queued_url_removes_it(session_scoped_session: Session) -> None:
    channel = create_random_channel(session_scoped_session)
    entry = create_random_channel_queue(session_scoped_session, channel)
    kept = create_random_channel_queue(session_scoped_session, channel)

    service.delete_queue_url(session_scoped_session, channel, entry.id)

    assert queued_urls(session_scoped_session, channel) == [kept.url]


# TODO: Validate
def test_deleting_a_url_that_is_not_queued_is_refused(
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        service.delete_queue_url(session_scoped_session, channel, uuid.uuid4())
    assert error.value.status_code == status.HTTP_404_NOT_FOUND


# TODO: Validate
def test_deleting_another_channels_queued_url_is_refused(
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(session_scoped_session)
    other = create_random_channel(session_scoped_session)
    entry = create_random_channel_queue(session_scoped_session, other)

    with pytest.raises(HTTPException) as error:
        service.delete_queue_url(session_scoped_session, channel, entry.id)

    assert error.value.status_code == status.HTTP_404_NOT_FOUND
    assert queued_urls(session_scoped_session, other) == [entry.url]


# TODO: Validate
def test_clearing_the_queue_drops_only_what_was_imported(
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(session_scoped_session)
    imported = create_random_channel_queue(
        session_scoped_session,
        channel,
        status=URLStatus.IMPORTED,
    )
    pending = create_random_channel_queue(
        session_scoped_session,
        channel,
        status=URLStatus.PENDING,
    )

    service.clear_completed_queue(session_scoped_session, channel)

    remaining = queued_urls(session_scoped_session, channel)
    assert imported.url not in remaining
    assert remaining == [pending.url]


# TODO: Validate
def test_a_bulk_import_queues_urls_on_each_channel(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    first = create_random_channel(session_scoped_session, user=owner.id)
    second = create_random_channel(session_scoped_session, user=owner.id)
    first_url = random_lower_string()
    second_url = random_lower_string()

    service.bulk_import_queue_urls(
        session_scoped_session,
        owner,
        {first.id: [first_url], second.id: [second_url]},
    )

    assert queued_urls(session_scoped_session, first) == [first_url]
    assert queued_urls(session_scoped_session, second) == [second_url]


# TODO: Validate
def test_a_bulk_import_refuses_a_channel_that_is_not_the_users(
    session_scoped_session: Session,
) -> None:
    owner = create_random_user(session_scoped_session)
    somebody_elses = create_random_channel(session_scoped_session)

    with pytest.raises(HTTPException) as error:
        service.bulk_import_queue_urls(
            session_scoped_session,
            owner,
            {somebody_elses.id: [random_lower_string()]},
        )

    assert error.value.status_code == status.HTTP_404_NOT_FOUND
    assert queued_urls(session_scoped_session, somebody_elses) == []
