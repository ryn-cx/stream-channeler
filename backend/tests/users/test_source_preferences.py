# TODO: Validate
# TODO: This is entirely AI generated and is probably garbage.
"""Tests for per-user source priority / enable-disable preferences."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.episode_selector import deduplicate_episodes, source_dedup_config
from app.config import settings
from app.episodes.models import Episode
from app.models import Visibility
from app.sources.service import OTHER_SOURCE_KEY, source_keys
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import SourcePreference
from app.users.service import effective_source_preferences
from tests.app.plugins.utils import create_random_plugin
from tests.app.sources.utils import create_random_source
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.utils import build_random_model

SOURCE_PREFERENCES_URL = f"{settings.API_V1_STR}/users/me/source-preferences"


def _auth_headers(client: TestClient, session: Session) -> dict[str, str]:
    user = create_random_user(session)
    return authentication_token_from_email(
        client=client,
        email=user.email,
        session=session,
    )


def _episode(identifier: str) -> Episode:
    return build_random_model(Episode, episode_identifier=identifier, deleted_at=None)


def _installed_source_keys(session: Session, count: int) -> list[str]:
    """Create `count` sources owned by the plugin user and return their keys."""
    plugin_user = user_service.get_or_create_plugin_user(session=session)
    keys: list[str] = []
    for _ in range(count):
        plugin = create_random_plugin(
            session,
            plugin_user,
            visibility=Visibility.public,
        )
        keys.append(create_random_source(session, plugin).key)
    return keys


def _private_source_key(session: Session, user: User) -> str:
    plugin = create_random_plugin(session, user, visibility=Visibility.public)
    return create_random_source(session, plugin).key


# --- source_keys ----------------------------------------------------------


def test_source_keys_come_from_the_database(session_scoped_session: Session) -> None:
    created = _installed_source_keys(session_scoped_session, 2)
    keys = source_keys(session_scoped_session)

    assert set(created) <= set(keys)
    # `Other` is a synthetic bucket, never a stored source key.
    assert OTHER_SOURCE_KEY not in keys


def test_source_keys_exclude_user_owned_plugins(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    private_key = _private_source_key(session_scoped_session, user)

    assert private_key not in source_keys(session_scoped_session)


def test_source_keys_exclude_deleted_sources(
    session_scoped_session: Session,
) -> None:
    plugin_user = user_service.get_or_create_plugin_user(session=session_scoped_session)
    plugin = create_random_plugin(
        session_scoped_session,
        plugin_user,
        visibility=Visibility.public,
    )
    source = create_random_source(session_scoped_session, plugin)
    assert source.key in source_keys(session_scoped_session)

    source.deleted_at = source.created_at
    session_scoped_session.add(source)
    session_scoped_session.flush()

    assert source.key not in source_keys(session_scoped_session)


# --- effective_source_preferences -----------------------------------------


def test_effective_defaults_include_every_source_enabled(
    session_scoped_session: Session,
) -> None:
    _installed_source_keys(session_scoped_session, 2)
    preferences = effective_source_preferences(session_scoped_session, [])
    keys = [preference.source_key for preference in preferences]

    assert keys == [*source_keys(session_scoped_session), OTHER_SOURCE_KEY]
    assert all(preference.enabled for preference in preferences)
    assert keys[-1] == OTHER_SOURCE_KEY


def test_effective_respects_stored_order_and_enabled(
    session_scoped_session: Session,
) -> None:
    _installed_source_keys(session_scoped_session, 2)
    installed = source_keys(session_scoped_session)
    # Reverse the stored order and disable the first one.
    stored = [
        SourcePreference(source_key=key, enabled=index != 0)
        for index, key in enumerate(reversed(installed))
    ]
    stored.append(SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=False))

    preferences = effective_source_preferences(session_scoped_session, stored)
    keys = [preference.source_key for preference in preferences]

    assert keys == [*reversed(installed), OTHER_SOURCE_KEY]
    by_key = {preference.source_key: preference.enabled for preference in preferences}
    assert by_key[installed[-1]] is False  # first stored entry was disabled
    assert by_key[OTHER_SOURCE_KEY] is False


def test_effective_drops_unknown_keys_and_appends_missing(
    session_scoped_session: Session,
) -> None:
    _installed_source_keys(session_scoped_session, 2)
    installed = source_keys(session_scoped_session)
    stored = [
        SourcePreference(source_key="NotARealSource", enabled=True),
        SourcePreference(source_key=installed[0], enabled=False),
    ]

    preferences = effective_source_preferences(session_scoped_session, stored)
    keys = [preference.source_key for preference in preferences]

    assert "NotARealSource" not in keys
    # The stored valid key keeps its position/flag; everything else is appended.
    assert keys[0] == installed[0]
    assert keys[-1] == OTHER_SOURCE_KEY
    assert set(keys) == {*installed, OTHER_SOURCE_KEY}
    assert preferences[0].enabled is False


def test_effective_new_source_appears_appended_and_enabled(
    session_scoped_session: Session,
) -> None:
    _installed_source_keys(session_scoped_session, 2)
    installed = source_keys(session_scoped_session)
    # A config stored before `new_source` existed: it is absent from the stored
    # rows but must still surface, enabled, with no change to what's stored.
    new_source = installed[-1]
    stored = [
        SourcePreference(source_key=key, enabled=True)
        for key in installed
        if key != new_source
    ]
    stored.append(SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=True))

    preferences = effective_source_preferences(session_scoped_session, stored)
    by_key = {preference.source_key: preference for preference in preferences}
    keys = [preference.source_key for preference in preferences]

    assert new_source in by_key
    assert by_key[new_source].enabled is True
    # The unconfigured source is appended at the end.
    assert keys[-1] == new_source


# --- source_dedup_config --------------------------------------------------


def test_dedup_config_priority_and_enabled_sets(
    session_scoped_session: Session,
) -> None:
    installed = _installed_source_keys(session_scoped_session, 2)
    stored = [
        SourcePreference(source_key=installed[0], enabled=False),
        SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=True),
    ]
    config = source_dedup_config(session_scoped_session, stored)

    # Lower index == higher priority; the disabled key still has a rank.
    assert config.priority[installed[0]] < config.priority[OTHER_SOURCE_KEY]
    assert installed[0] in config.disabled_keys
    assert installed[0] not in config.enabled_keys
    assert config.other_enabled is True
    # Unknown keys fall back to Other's priority.
    assert config.priority_for("SomethingCustom") == config.other_priority
    assert config.priority_for(None) == config.other_priority


# --- deduplicate_episodes -------------------------------------------------


def test_deduplicate_keeps_higher_priority_source(
    session_scoped_session: Session,
) -> None:
    _installed_source_keys(session_scoped_session, 2)
    config = source_dedup_config(session_scoped_session, [])
    installed = source_keys(session_scoped_session)
    higher, lower = installed[0], installed[1]

    lower_episode = _episode("TMDB shared")
    higher_episode = _episode("TMDB shared")
    episode_source_keys = {lower_episode.id: lower, higher_episode.id: higher}

    # Even though the lower-priority source comes first, the higher wins.
    result = deduplicate_episodes(
        [lower_episode, higher_episode],
        episode_source_keys,
        config,
    )

    assert len(result) == 1
    assert result[0].id == higher_episode.id


def test_deduplicate_preserves_order_and_removes_duplicates(
    session_scoped_session: Session,
) -> None:
    installed = _installed_source_keys(session_scoped_session, 1)
    config = source_dedup_config(session_scoped_session, [])
    first = _episode("TMDB 1")
    second = _episode("TMDB 2")
    duplicate_of_first = _episode("TMDB 1")
    episode_source_keys = {
        first.id: installed[0],
        second.id: installed[0],
        duplicate_of_first.id: installed[0],
    }

    result = deduplicate_episodes(
        [first, second, duplicate_of_first],
        episode_source_keys,
        config,
    )

    assert [episode.episode_identifier for episode in result] == ["TMDB 1", "TMDB 2"]


def test_deduplicate_distinct_identifiers_all_kept(
    session_scoped_session: Session,
) -> None:
    config = source_dedup_config(session_scoped_session, [])
    episodes = [_episode(f"TMDB {index}") for index in range(3)]
    episode_source_keys = {episode.id: OTHER_SOURCE_KEY for episode in episodes}

    result = deduplicate_episodes(episodes, episode_source_keys, config)

    assert len(result) == len(episodes)


# --- API endpoints --------------------------------------------------------


def test_read_source_preferences_returns_defaults(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    _installed_source_keys(session_scoped_session, 2)
    response = session_scoped_client.get(SOURCE_PREFERENCES_URL, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    keys = [item["source_key"] for item in response.json()]
    assert keys == [*source_keys(session_scoped_session), OTHER_SOURCE_KEY]
    assert all(item["enabled"] for item in response.json())


def test_update_source_preferences_round_trips(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    installed = _installed_source_keys(session_scoped_session, 2)
    payload = [
        {"source_key": OTHER_SOURCE_KEY, "enabled": False},
        {"source_key": installed[0], "enabled": False},
    ]
    response = session_scoped_client.put(
        SOURCE_PREFERENCES_URL,
        headers=headers,
        json=payload,
    )
    assert response.status_code == status.HTTP_200_OK

    returned = {item["source_key"]: item["enabled"] for item in response.json()}
    assert returned[OTHER_SOURCE_KEY] is False
    assert returned[installed[0]] is False

    # The stored order is honored on the next read.
    keys = [
        item["source_key"]
        for item in session_scoped_client.get(
            SOURCE_PREFERENCES_URL,
            headers=headers,
        ).json()
    ]
    assert keys[0] == OTHER_SOURCE_KEY
    assert keys[1] == installed[0]


def test_update_source_preferences_rejects_unknown_key(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    response = session_scoped_client.put(
        SOURCE_PREFERENCES_URL,
        headers=headers,
        json=[{"source_key": "NotARealSource", "enabled": True}],
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_update_source_preferences_rejects_duplicate_key(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    response = session_scoped_client.put(
        SOURCE_PREFERENCES_URL,
        headers=headers,
        json=[
            {"source_key": OTHER_SOURCE_KEY, "enabled": True},
            {"source_key": OTHER_SOURCE_KEY, "enabled": False},
        ],
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_source_preferences_require_authentication(
    session_scoped_client: TestClient,
) -> None:
    assert session_scoped_client.get(SOURCE_PREFERENCES_URL).status_code in {
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    }
