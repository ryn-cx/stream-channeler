# TODO: This is entirely AI generated and is probably garbage.
"""Tests for per-user source priority / enable-disable preferences."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.episode_selector import deduplicate_episodes, source_dedup_config
from app.config import settings
from app.episodes.models import Episode
from app.sources.service import OTHER_SOURCE_KEY, official_source_keys
from app.users.schemas import SourcePreference
from app.users.service import effective_source_preferences
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.utils import build_random_model

SOURCE_PREFERENCES_URL = f"{settings.API_V1_STR}/users/me/source-preferences"
_MINIMUM_SOURCES = 2


def _auth_headers(client: TestClient, session: Session) -> dict[str, str]:
    user = create_random_user(session)
    return authentication_token_from_email(
        client=client,
        email=user.email,
        session=session,
    )


def _episode(identifier: str) -> Episode:
    return build_random_model(Episode, episode_identifier=identifier, deleted_at=None)


# --- official_source_keys -------------------------------------------------


def test_official_source_keys_exclude_lookup_only_plugins() -> None:
    keys = official_source_keys()
    assert keys, "expected at least one official source plugin"
    # TMDB is lookup-only (no import_url) so it can never own episodes.
    assert "TMDB" not in keys
    # `Other` is a synthetic bucket, never a real plugin key.
    assert OTHER_SOURCE_KEY not in keys


# --- effective_source_preferences -----------------------------------------


def test_effective_defaults_include_every_source_enabled() -> None:
    preferences = effective_source_preferences([])
    keys = [preference.source_key for preference in preferences]

    assert keys == [*official_source_keys(), OTHER_SOURCE_KEY]
    assert all(preference.enabled for preference in preferences)
    assert keys[-1] == OTHER_SOURCE_KEY


def test_effective_respects_stored_order_and_enabled() -> None:
    official = official_source_keys()
    # Reverse the official order and disable the first one.
    stored = [
        SourcePreference(source_key=key, enabled=index != 0)
        for index, key in enumerate(reversed(official))
    ]
    stored.append(SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=False))

    preferences = effective_source_preferences(stored)
    keys = [preference.source_key for preference in preferences]

    assert keys == [*reversed(official), OTHER_SOURCE_KEY]
    by_key = {preference.source_key: preference.enabled for preference in preferences}
    assert by_key[official[-1]] is False  # first stored entry was disabled
    assert by_key[OTHER_SOURCE_KEY] is False


def test_effective_drops_unknown_keys_and_appends_missing() -> None:
    official = official_source_keys()
    stored = [
        SourcePreference(source_key="NotARealPlugin", enabled=True),
        SourcePreference(source_key=official[0], enabled=False),
    ]

    preferences = effective_source_preferences(stored)
    keys = [preference.source_key for preference in preferences]

    assert "NotARealPlugin" not in keys
    # The stored valid key keeps its position/flag; everything else is appended.
    assert keys[0] == official[0]
    assert keys[-1] == OTHER_SOURCE_KEY
    assert set(keys) == {*official, OTHER_SOURCE_KEY}
    assert preferences[0].enabled is False


def test_effective_new_plugin_appears_appended_and_enabled() -> None:
    official = official_source_keys()
    if len(official) < _MINIMUM_SOURCES:
        pytest.skip("needs at least two official source plugins")
    # A config stored before `new_plugin` existed: it is absent from the stored
    # rows but must still surface, enabled, with no change to what's stored.
    new_plugin = official[-1]
    stored = [
        SourcePreference(source_key=key, enabled=True)
        for key in official
        if key != new_plugin
    ]
    stored.append(SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=True))

    preferences = effective_source_preferences(stored)
    by_key = {preference.source_key: preference for preference in preferences}
    keys = [preference.source_key for preference in preferences]

    assert new_plugin in by_key
    assert by_key[new_plugin].enabled is True
    # The unconfigured plugin is appended at the end.
    assert keys[-1] == new_plugin


# --- source_dedup_config --------------------------------------------------


def test_dedup_config_priority_and_enabled_sets() -> None:
    official = official_source_keys()
    stored = [
        SourcePreference(source_key=official[0], enabled=False),
        SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=True),
    ]
    config = source_dedup_config(stored)

    # Lower index == higher priority; the disabled official key still has a rank.
    assert config.priority[official[0]] < config.priority[OTHER_SOURCE_KEY]
    assert official[0] in config.disabled_keys
    assert official[0] not in config.enabled_keys
    assert config.other_enabled is True
    # Unknown keys fall back to Other's priority.
    assert config.priority_for("SomethingCustom") == config.other_priority
    assert config.priority_for(None) == config.other_priority


# --- deduplicate_episodes -------------------------------------------------


def test_deduplicate_keeps_higher_priority_source() -> None:
    official = official_source_keys()
    higher, lower = official[0], official[1]
    config = source_dedup_config([])

    lower_episode = _episode("TMDB shared")
    higher_episode = _episode("TMDB shared")
    plugin_keys = {lower_episode.id: lower, higher_episode.id: higher}

    # Even though the lower-priority source comes first, the higher wins.
    result = deduplicate_episodes([lower_episode, higher_episode], plugin_keys, config)

    assert len(result) == 1
    assert result[0].id == higher_episode.id


def test_deduplicate_preserves_order_and_removes_duplicates() -> None:
    config = source_dedup_config([])
    first = _episode("TMDB 1")
    second = _episode("TMDB 2")
    duplicate_of_first = _episode("TMDB 1")
    official = official_source_keys()
    plugin_keys = {
        first.id: official[0],
        second.id: official[0],
        duplicate_of_first.id: official[0],
    }

    result = deduplicate_episodes(
        [first, second, duplicate_of_first],
        plugin_keys,
        config,
    )

    assert [episode.episode_identifier for episode in result] == ["TMDB 1", "TMDB 2"]


def test_deduplicate_distinct_identifiers_all_kept() -> None:
    config = source_dedup_config([])
    episodes = [_episode(f"TMDB {index}") for index in range(3)]
    plugin_keys = {episode.id: OTHER_SOURCE_KEY for episode in episodes}

    result = deduplicate_episodes(episodes, plugin_keys, config)

    assert len(result) == len(episodes)


# --- API endpoints --------------------------------------------------------


def test_read_source_preferences_returns_defaults(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    response = session_scoped_client.get(SOURCE_PREFERENCES_URL, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    keys = [item["source_key"] for item in response.json()]
    assert keys == [*official_source_keys(), OTHER_SOURCE_KEY]
    assert all(item["enabled"] for item in response.json())


def test_update_source_preferences_round_trips(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    official = official_source_keys()
    payload = [
        {"source_key": OTHER_SOURCE_KEY, "enabled": False},
        {"source_key": official[0], "enabled": False},
    ]
    response = session_scoped_client.put(
        SOURCE_PREFERENCES_URL,
        headers=headers,
        json=payload,
    )
    assert response.status_code == status.HTTP_200_OK

    returned = {item["source_key"]: item["enabled"] for item in response.json()}
    assert returned[OTHER_SOURCE_KEY] is False
    assert returned[official[0]] is False

    # The stored order is honored on the next read.
    keys = [
        item["source_key"]
        for item in session_scoped_client.get(
            SOURCE_PREFERENCES_URL,
            headers=headers,
        ).json()
    ]
    assert keys[0] == OTHER_SOURCE_KEY
    assert keys[1] == official[0]


def test_update_source_preferences_rejects_unknown_key(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    headers = _auth_headers(session_scoped_client, session_scoped_session)
    response = session_scoped_client.put(
        SOURCE_PREFERENCES_URL,
        headers=headers,
        json=[{"source_key": "NotARealPlugin", "enabled": True}],
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
