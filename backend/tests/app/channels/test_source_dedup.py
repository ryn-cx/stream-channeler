# TODO: This is entirely AI generated and is probably garbage.
"""Integration tests for source deduplication and global enable/disable.

Exercises `EpisodeQueryBuilder` end to end: the same episode (shared
`episode_identifier`) offered by two sources must collapse to one, the winner
follows the user's source priority, disabling a source hides it globally, and
the per-channel `source_ids` filter still stacks on top.
"""

import uuid

import pytest
from sqlmodel import Session

from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.models import Visibility
from app.shows.models import Show
from app.sources.service import official_source_keys
from app.users.models import User, UserSourcePreference
from app.users.schemas import SourcePreference
from tests.app.channels.utils import create_random_channel, create_random_channel_show
from tests.app.episodes.utils import create_random_episode
from tests.app.plugins.utils import create_random_plugin
from tests.app.users.utils import create_random_user

SHARED_IDENTIFIER = "TMDB shared-episode"
_MINIMUM_SOURCES = 2


def _two_official_keys() -> tuple[str, str]:
    keys = official_source_keys()
    if len(keys) < _MINIMUM_SOURCES:
        pytest.skip("needs at least two official source plugins")
    return keys[0], keys[1]


def _build_duplicated_channel(
    session: Session,
    user: User,
) -> tuple[Channel, dict[str, Show]]:
    """A channel with the same episode imported from two official sources."""
    channel = create_random_channel(session, user, is_public=False)
    shows: dict[str, Show] = {}
    for key in _two_official_keys():
        plugin = create_random_plugin(
            session,
            user,
            key=key,
            visibility=Visibility.public,
        )
        channel_show = create_random_channel_show(
            session,
            channel,
            plugin,
            is_whitelist=False,
        )
        create_random_episode(
            session,
            channel_show.show,
            episode_identifier=SHARED_IDENTIFIER,
        )
        shows[key] = channel_show.show
    return channel, shows


def _set_preferences(
    session: Session,
    user: User,
    preferences: list[SourcePreference],
) -> None:
    user.source_preferences = [
        UserSourcePreference(
            source_key=preference.source_key,
            priority=index,
            enabled=preference.enabled,
        )
        for index, preference in enumerate(preferences)
    ]
    session.add(user)
    session.flush()


def _selected_show_ids(
    session: Session,
    channel: Channel,
    user: User,
    channel_options: ChannelOptions | None = None,
) -> list[uuid.UUID]:
    builder = EpisodeQueryBuilder(
        session,
        channel,
        channel_options or ChannelOptions(),
        user,
    )
    return [result.episode.season.show.id for result in builder.get_episodes()]


def test_duplicate_episode_collapses_to_priority_source(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    channel, shows = _build_duplicated_channel(session_scoped_session, user)
    key_a, key_b = _two_official_keys()

    # Prioritize key_b over key_a.
    _set_preferences(
        session_scoped_session,
        user,
        [
            SourcePreference(source_key=key_b, enabled=True),
            SourcePreference(source_key=key_a, enabled=True),
        ],
    )

    show_ids = _selected_show_ids(session_scoped_session, channel, user)

    assert show_ids == [shows[key_b].id]


def test_disabled_source_is_hidden_globally(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    channel, shows = _build_duplicated_channel(session_scoped_session, user)
    key_a, key_b = _two_official_keys()

    # key_b is the higher priority but globally disabled, so key_a wins instead.
    _set_preferences(
        session_scoped_session,
        user,
        [
            SourcePreference(source_key=key_b, enabled=False),
            SourcePreference(source_key=key_a, enabled=True),
        ],
    )

    show_ids = _selected_show_ids(session_scoped_session, channel, user)

    assert show_ids == [shows[key_a].id]


def test_channel_source_filter_stacks_on_top_of_preferences(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    channel, shows = _build_duplicated_channel(session_scoped_session, user)
    key_a, key_b = _two_official_keys()

    # Globally key_b wins, but the channel blacklists key_b's source, so the
    # per-channel filter narrows the result to key_a.
    _set_preferences(
        session_scoped_session,
        user,
        [
            SourcePreference(source_key=key_b, enabled=True),
            SourcePreference(source_key=key_a, enabled=True),
        ],
    )
    options = ChannelOptions(
        source_ids=[shows[key_b].source_id],
        source_ids_is_blacklist=True,
    )

    show_ids = _selected_show_ids(session_scoped_session, channel, user, options)

    assert show_ids == [shows[key_a].id]
