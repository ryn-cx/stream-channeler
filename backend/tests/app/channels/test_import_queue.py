# TODO: Validate
"""What working a channel's import queue does to the entries in it.

Importing a URL is the plugin's own work and is tested against the plugins. What
is here is the queue around it: which entries are picked up, and what an entry
nothing can import is left saying.
"""

from datetime import timedelta

from sqlmodel import Session

from app.channels.models import URLStatus
from app.tools.import_queue import import_queue
from app.utils import tz_datetime
from tests.app.channels.utils import create_random_channel, create_random_channel_queue
from tests.app.helpers.utils import random_lower_string


# TODO: Validate
def test_a_url_no_plugin_can_import_is_failed(
    function_scoped_session: Session,
) -> None:
    channel = create_random_channel(function_scoped_session)
    item = create_random_channel_queue(
        function_scoped_session,
        channel,
        url=random_lower_string(),
        status=URLStatus.PENDING,
        import_at=None,
    )
    function_scoped_session.commit()

    import_queue(function_scoped_session)

    function_scoped_session.refresh(item)
    assert item.status == URLStatus.FAILED
    assert item.note == "No valid plugin found."


# TODO: Validate
def test_an_entry_waiting_for_its_turn_is_left_alone(
    function_scoped_session: Session,
) -> None:
    """An entry rescheduled for later is not picked up before then."""
    channel = create_random_channel(function_scoped_session)
    item = create_random_channel_queue(
        function_scoped_session,
        channel,
        url=random_lower_string(),
        status=URLStatus.PENDING,
        import_at=tz_datetime.now() + timedelta(hours=1),
    )
    function_scoped_session.commit()

    import_queue(function_scoped_session)

    function_scoped_session.refresh(item)
    assert item.status == URLStatus.PENDING


# TODO: Validate
def test_an_entry_already_imported_is_not_picked_up_again(
    function_scoped_session: Session,
) -> None:
    channel = create_random_channel(function_scoped_session)
    item = create_random_channel_queue(
        function_scoped_session,
        channel,
        url=random_lower_string(),
        status=URLStatus.IMPORTED,
        import_at=None,
    )
    function_scoped_session.commit()

    import_queue(function_scoped_session)

    function_scoped_session.refresh(item)
    assert item.status == URLStatus.IMPORTED


# TODO: Validate
def test_an_entry_that_already_failed_is_not_failed_again(
    function_scoped_session: Session,
) -> None:
    channel = create_random_channel(function_scoped_session)
    note = random_lower_string()
    item = create_random_channel_queue(
        function_scoped_session,
        channel,
        url=random_lower_string(),
        status=URLStatus.FAILED,
        note=note,
        import_at=None,
    )
    function_scoped_session.commit()

    import_queue(function_scoped_session)

    function_scoped_session.refresh(item)
    assert item.note == note
