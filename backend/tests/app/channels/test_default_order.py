# TODO: Validate
"""What the channel service stores as a channel's default order."""

import json
from typing import Literal

import pytest
from sqlmodel import Session

from app.channels import service
from app.channels.schemas import ChannelOptions
from tests.app.channels.utils import create_random_channel
from tests.app.helpers.utils import build_random_model


# TODO: Validate
@pytest.mark.parametrize("mode", ["minimal", "full"])
def test_setting_a_default_order_stores_what_was_chosen(
    session_scoped_session: Session,
    mode: Literal["minimal", "full"],
) -> None:
    """Only the fields that were set go down; a whole order is not written out."""
    channel = create_random_channel(session_scoped_session)
    options = build_random_model(ChannelOptions, mode)

    updated = service.set_default_order(session_scoped_session, channel, options)

    stored = json.loads(updated.default_order or "")
    assert isinstance(stored, dict)
    assert bool(stored) == (mode == "full")


# TODO: Validate
def test_setting_a_default_order_replaces_the_one_before_it(
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(session_scoped_session)
    service.set_default_order(
        session_scoped_session,
        channel,
        ChannelOptions(hide_watched=True),
    )
    updated = service.set_default_order(
        session_scoped_session,
        channel,
        ChannelOptions(hide_unwatched=True),
    )

    stored = json.loads(updated.default_order or "{}")
    assert stored.get("hideUnwatched") is True
    assert "hideWatched" not in stored


# TODO: Validate
def test_a_seed_that_was_never_given_is_not_stored(
    session_scoped_session: Session,
) -> None:
    """A random seed nobody chose would freeze the shuffle it is meant to vary."""
    channel = create_random_channel(session_scoped_session)
    updated = service.set_default_order(
        session_scoped_session,
        channel,
        ChannelOptions(hide_watched=True),
    )
    assert "randomSeed" not in json.loads(updated.default_order or "{}")


# TODO: Validate
def test_a_seed_that_was_given_is_stored(session_scoped_session: Session) -> None:
    channel = create_random_channel(session_scoped_session)
    updated = service.set_default_order(
        session_scoped_session,
        channel,
        ChannelOptions(random_seed=1234),
    )
    assert json.loads(updated.default_order or "{}")["randomSeed"] == 1234  # noqa: PLR2004 - The number is the point of the test.
