# TODO: Validate
# TODO: This was completely AI generated just to have a temporary baseline and should be
# replaced with real tests.
import uuid

from sqlmodel import Session, select

from app.channels.models import ChannelQueue, ChannelShow, URLStatus
from app.tools.import_queue import import_queue
from tests.app.channels.utils import create_random_channel
from tests.app.shows.utils import create_random_show
from tests.app.utils.utils import random_lower_string


def _queue(
    session: Session,
    channel_id: uuid.UUID,
    url: str,
) -> ChannelQueue:
    item = ChannelQueue(channel_id=channel_id, url=url, status=URLStatus.PENDING)
    session.add(item)
    session.commit()
    return item


class TestImportQueue:
    def test_imports_matching_url_into_channel(
        self,
        function_scoped_session: Session,
    ) -> None:
        show = create_random_show(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        item = _queue(
            function_scoped_session,
            channel.id,
            f"streamchanneler.com/show/{show.id}/",
        )

        import_queue(function_scoped_session)

        function_scoped_session.refresh(item)
        assert item.status == URLStatus.IMPORTED

        channel_shows = function_scoped_session.exec(
            select(ChannelShow).where(ChannelShow.channel_id == channel.id),
        ).all()
        assert len(channel_shows) == 1
        assert channel_shows[0].show_identifier == show.show_identifier

    def test_uses_the_callers_session_database(
        self,
        function_scoped_session: Session,
    ) -> None:
        # The show exists only inside this test's uncommitted transaction. If the import
        # ran on a different engine/connection it could not find it and would fail, so a
        # successful import proves the caller's session (and its database) is used.
        show = create_random_show(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        item = _queue(
            function_scoped_session,
            channel.id,
            f"streamchanneler.com/show/{show.id}/",
        )

        import_queue(function_scoped_session)

        function_scoped_session.refresh(item)
        assert item.status == URLStatus.IMPORTED

    def test_only_imports_the_matching_plugin(
        self,
        function_scoped_session: Session,
    ) -> None:
        # Two shows, only one queued; importing StreamChanneler must import exactly the
        # queued one and leave nothing else pending.
        show = create_random_show(function_scoped_session)
        create_random_show(function_scoped_session)
        channel = create_random_channel(function_scoped_session)
        item = _queue(
            function_scoped_session,
            channel.id,
            f"streamchanneler.com/show/{show.id}/",
        )

        import_queue(function_scoped_session)

        function_scoped_session.refresh(item)
        assert item.status == URLStatus.IMPORTED
        channel_shows = function_scoped_session.exec(
            select(ChannelShow).where(ChannelShow.channel_id == channel.id),
        ).all()
        assert {channel_show.show_identifier for channel_show in channel_shows} == {
            show.show_identifier,
        }

    def test_marks_unmatched_url_failed(
        self,
        function_scoped_session: Session,
    ) -> None:
        channel = create_random_channel(function_scoped_session)
        item = _queue(function_scoped_session, channel.id, random_lower_string())

        import_queue(function_scoped_session)

        function_scoped_session.refresh(item)
        assert item.status == URLStatus.FAILED
        assert item.note == "No valid plugin found."

    def test_marks_invalid_url_failed(
        self,
        function_scoped_session: Session,
    ) -> None:
        # Correct StreamChanneler URL shape, but the show does not exist, so the plugin
        # raises InvalidURLError and the item is failed rather than importing.
        channel = create_random_channel(function_scoped_session)
        item = _queue(
            function_scoped_session,
            channel.id,
            f"streamchanneler.com/show/{uuid.uuid4()}/",
        )

        import_queue(function_scoped_session)

        function_scoped_session.refresh(item)
        assert item.status == URLStatus.FAILED
        assert item.note == "Invalid URL."
