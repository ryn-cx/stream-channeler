# TODO: Validate
from collections.abc import Generator
from typing import Any, NamedTuple

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from app.users.models import User
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

CHANNEL_URL = "https://www.youtube.com/@jawed"
EPISODE_KEY = "jNQXAC9IVRw"
EXPECTED_COPIES = 2
EXPECTED_SEASONS = 2


# TODO: Validate
class ImportedChannel(NamedTuple):
    client: TestClient
    headers: dict[str, str]
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
        if episode["key"] == EPISODE_KEY
    ]


# TODO: Validate
@pytest.fixture
def imported_channel(
    function_scoped_client: TestClient,
    function_scoped_session: Session,
) -> ImportedChannel:
    user = create_logged_in_user(function_scoped_client, function_scoped_session)
    channel_id = create_channel(
        function_scoped_session,
        function_scoped_session.get_one(User, user.id),
    )
    import_url(
        function_scoped_client,
        function_scoped_session,
        user.headers,
        channel_id,
        CHANNEL_URL,
    )
    seasons = whitelist_every_season(function_scoped_client, user.headers, channel_id)
    assert seasons == EXPECTED_SEASONS
    return ImportedChannel(function_scoped_client, user.headers, channel_id)


# TODO: Validate
@pytest.fixture
def started_watch(imported_channel: ImportedChannel) -> str:
    episode = _channel_episodes(imported_channel)[0]
    response = imported_channel.client.post(
        f"{settings.API_V1_STR}/episodes/{episode['id']}/watches",
        headers=imported_channel.headers,
        json={"verified": False},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    watch = response.json()[0]
    assert watch["verified"] is False
    assert isinstance(watch["id"], str)
    return watch["id"]


# TODO: Validate
@pytest.fixture
def verified_watch(imported_channel: ImportedChannel, started_watch: str) -> str:
    response = imported_channel.client.patch(
        f"{settings.API_V1_STR}/watches/{started_watch}",
        headers=imported_channel.headers,
        json={"verified": True},
    )
    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json()[0]["verified"] is True
    return started_watch


# TODO: Validate
def test_episode_is_listed_once_per_season(imported_channel: ImportedChannel) -> None:
    episodes = _channel_episodes(imported_channel)
    assert len(episodes) == EXPECTED_COPIES
    assert len({episode["id"] for episode in episodes}) == EXPECTED_COPIES


# TODO: Validate
def test_started_watch_covers_every_copy(
    imported_channel: ImportedChannel,
    started_watch: str,
) -> None:
    episodes = _channel_episodes(imported_channel)
    assert len(episodes) == EXPECTED_COPIES
    assert all(episode["episode_watch_id"] == started_watch for episode in episodes)
    assert all(episode["verified"] is False for episode in episodes)


# TODO: Validate
def test_started_only_keeps_a_started_watch(
    imported_channel: ImportedChannel,
    started_watch: str,
) -> None:
    episodes = _channel_episodes(
        imported_channel,
        hideWatched=True,
        hideUnwatched=True,
    )
    assert len(episodes) == EXPECTED_COPIES
    assert all(episode["episode_watch_id"] == started_watch for episode in episodes)


# TODO: Validate
def test_hide_partially_watched_hides_a_started_watch(
    imported_channel: ImportedChannel,
    started_watch: str,  # noqa: ARG001 - The watch is what the filter acts on.
) -> None:
    assert _channel_episodes(imported_channel, hidePartiallyWatched=True) == []


# TODO: Validate
def test_hide_partially_watched_keeps_a_verified_watch(
    imported_channel: ImportedChannel,
    verified_watch: str,
) -> None:
    episodes = _channel_episodes(imported_channel, hidePartiallyWatched=True)
    assert len(episodes) == EXPECTED_COPIES
    assert all(episode["episode_watch_id"] == verified_watch for episode in episodes)
    assert all(episode["verified"] is True for episode in episodes)


# TODO: Validate
def test_hide_watched_hides_a_verified_watch(
    imported_channel: ImportedChannel,
    verified_watch: str,  # noqa: ARG001 - The watch is what the filter acts on.
) -> None:
    assert _channel_episodes(imported_channel, hideWatched=True) == []


# TODO: Validate
def test_started_only_hides_a_verified_watch(
    imported_channel: ImportedChannel,
    verified_watch: str,  # noqa: ARG001 - The watch is what the filter acts on.
) -> None:
    assert (
        _channel_episodes(imported_channel, hideWatched=True, hideUnwatched=True) == []
    )
