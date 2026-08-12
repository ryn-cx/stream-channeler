# TODO: Validate
import uuid
from collections.abc import Generator
from typing import Any, NamedTuple
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.config import settings
from app.episodes.models import Episode
from app.users.models import User
from app.watches.models import Watch
from app.watches.schemas import WatchCreate, WatchUpdate
from app.watches.services import create_watch, update_watch
from tests.app.channels.utils import (
    create_channel,
    import_url,
    whitelist_every_season,
)
from tests.app.users.utils import create_logged_in_user
from tests.old_mess.plugins.plugin_validator.context_managers import (
    check_episodes_before_grouped_download,
    serve_downloads_from_disk,
)


# TODO: Validate
class ImportedChannel(NamedTuple):
    client: TestClient
    session: Session
    headers: dict[str, str]
    user_id: uuid.UUID
    channel_id: str


# TODO: Validate
@pytest.fixture(scope="module", autouse=True)
def _stored_downloads() -> Generator[None]:
    with check_episodes_before_grouped_download(), serve_downloads_from_disk():
        yield


# TODO: Validate
def _channel_episodes(
    channel: ImportedChannel,
    **options: bool,
) -> list[dict[str, Any]]:
    response = channel.client.get(
        f"{settings.API_V1_STR}/channels/{channel.channel_id}/episodes",
        headers=channel.headers,
        params=options,
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    return [
        episode
        for episode in response.json()["episodes"]
        if episode["key"] == TestWatchStatus.EPISODE_KEY
    ]


# TODO: Validate
class TestWatchStatus:
    CHANNEL_URL = "https://www.youtube.com/@jawed"
    EPISODE_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    EPISODE_KEY = parse_qs(urlparse(EPISODE_URL).query)["v"][0]
    EXPECTED_COPIES = 2

    # TODO: Validate
    class TestDuplicateEpisodeIdentifiers:
        # TODO: Validate
        @pytest.fixture(scope="class")
        def imported_channel(
            self,
            function_scoped_client: TestClient,
            function_scoped_session: Session,
        ) -> ImportedChannel:
            user = create_logged_in_user(
                function_scoped_client,
                function_scoped_session,
            )
            channel_id = create_channel(
                function_scoped_session,
                function_scoped_session.get_one(User, user.id),
            )
            import_url(
                function_scoped_client,
                function_scoped_session,
                user.headers,
                channel_id,
                TestWatchStatus.CHANNEL_URL,
            )
            whitelist_every_season(
                function_scoped_client,
                user.headers,
                channel_id,
            )
            return ImportedChannel(
                function_scoped_client,
                function_scoped_session,
                user.headers,
                user.id,
                channel_id,
            )

        # TODO: Validate
        @pytest.fixture
        def started_watch(self, imported_channel: ImportedChannel) -> Watch:
            episodes = imported_channel.session.exec(
                select(Episode).where(
                    col(Episode.key) == TestWatchStatus.EPISODE_KEY,
                ),
            ).all()
            episode = episodes[0]
            return create_watch(
                imported_channel.session,
                imported_channel.user_id,
                episode,
                WatchCreate(verified=False),
            )

        # TODO: Validate
        @pytest.fixture
        def verified_watch(
            self,
            imported_channel: ImportedChannel,
            started_watch: Watch,
        ) -> Watch:
            watch = update_watch(
                imported_channel.session,
                imported_channel.session.get_one(Watch, started_watch.id),
                WatchUpdate(verified=True),
            )
            assert watch.verified is True
            return started_watch

        # TODO: Validate
        def test_episode_is_listed_once_per_season(
            self,
            imported_channel: ImportedChannel,
        ) -> None:
            episodes = _channel_episodes(imported_channel)
            assert len(episodes) == TestWatchStatus.EXPECTED_COPIES
            assert (
                len({episode["id"] for episode in episodes})
                == TestWatchStatus.EXPECTED_COPIES
            )

        # TODO: Validate
        def test_started_watch_covers_every_copy(
            self,
            imported_channel: ImportedChannel,
            started_watch: Watch,
        ) -> None:
            episodes = _channel_episodes(imported_channel)
            assert len(episodes) == TestWatchStatus.EXPECTED_COPIES
            assert all(
                episode["episode_watch_id"] == str(started_watch.id)
                for episode in episodes
            )
            assert all(episode["verified"] is False for episode in episodes)

        # TODO: Validate
        def test_started_only_keeps_a_started_watch(
            self,
            imported_channel: ImportedChannel,
            started_watch: Watch,
        ) -> None:
            episodes = _channel_episodes(
                imported_channel,
                hideWatched=True,
                hideUnwatched=True,
            )
            assert len(episodes) == TestWatchStatus.EXPECTED_COPIES
            assert all(
                episode["episode_watch_id"] == str(started_watch.id)
                for episode in episodes
            )

        # TODO: Validate
        def test_hide_partially_watched_hides_a_started_watch(
            self,
            imported_channel: ImportedChannel,
            started_watch: Watch,  # noqa: ARG002 - The watch is what the filter acts on.
        ) -> None:
            assert _channel_episodes(imported_channel, hidePartiallyWatched=True) == []

        # TODO: Validate
        def test_hide_partially_watched_keeps_a_verified_watch(
            self,
            imported_channel: ImportedChannel,
            verified_watch: Watch,
        ) -> None:
            episodes = _channel_episodes(imported_channel, hidePartiallyWatched=True)
            assert len(episodes) == TestWatchStatus.EXPECTED_COPIES
            assert all(
                episode["episode_watch_id"] == str(verified_watch.id)
                for episode in episodes
            )
            assert all(episode["verified"] is True for episode in episodes)

        # TODO: Validate
        def test_hide_watched_hides_a_verified_watch(
            self,
            imported_channel: ImportedChannel,
            verified_watch: Watch,  # noqa: ARG002 - The watch is what the filter acts on.
        ) -> None:
            assert _channel_episodes(imported_channel, hideWatched=True) == []

        # TODO: Validate
        def test_started_only_hides_a_verified_watch(
            self,
            imported_channel: ImportedChannel,
            verified_watch: Watch,  # noqa: ARG002 - The watch is what the filter acts on.
        ) -> None:
            assert (
                _channel_episodes(
                    imported_channel,
                    hideWatched=True,
                    hideUnwatched=True,
                )
                == []
            )
