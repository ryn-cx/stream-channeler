# TODO: Validate
# TODO: This is entirely AI generated and is probably garbage.
"""Integration tests for source deduplication and global enable/disable.

Exercises `EpisodeQueryBuilder` end to end: the same episode (one canonical
episode) offered by two sources must collapse to one, the winner
follows the user's source priority, disabling a source hides it globally, and
the per-channel `source_ids` filter still stacks on top.
"""

import uuid

from sqlmodel import Session

from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel
from app.channels.schemas import ChannelOptions
from app.episodes.models import Episode
from app.models import Visibility
from app.seasons.models import Season
from app.shows.models import Show
from app.users import service as user_service
from app.users.models import User, UserSourcePreference
from app.users.schemas import SourcePreference
from tests.old_mess.app.channels.utils import (
    channel_show_show,
    create_random_channel,
    create_random_channel_show,
)
from tests.old_mess.app.episodes.utils import create_random_episode
from tests.old_mess.app.plugins.utils import create_random_plugin
from tests.old_mess.app.sources.utils import create_random_source
from tests.old_mess.app.users.utils import create_random_user

SOURCE_KEY_A = "DedupTestSourceA"
SOURCE_KEY_B = "DedupTestSourceB"


# TODO: Validate
def _build_duplicated_channel(
    session: Session,
    user: User,
) -> tuple[Channel, dict[str, Show]]:
    """Build a channel with the same episode imported from two installed sources."""
    channel = create_random_channel(session, user, is_public=False)
    plugin_user = user_service.get_or_create_plugin_user(session=session)
    # The one episode both sources carry a copy of. Made up front so the two
    # copies can be pointed at it, which is what they would share after an
    # import reconciled them.
    shared_plugin = create_random_plugin(
        session,
        plugin_user,
        visibility=Visibility.public,
    )
    shared_source = create_random_source(session, shared_plugin)
    shared_show = Show(key=f"Dedup {uuid.uuid4()}", source_id=shared_source.id)
    session.add(shared_show)
    session.flush()
    shared_season = Season(key=f"Dedup {uuid.uuid4()}", show_id=shared_show.id)
    session.add(shared_season)
    session.flush()
    shared_episode = Episode(key=f"Dedup {uuid.uuid4()}", season_id=shared_season.id)
    session.add(shared_episode)
    session.flush()
    shows: dict[str, Show] = {}
    for key in (SOURCE_KEY_A, SOURCE_KEY_B):
        plugin = create_random_plugin(
            session,
            plugin_user,
            visibility=Visibility.public,
        )
        source = create_random_source(session, plugin, key=key)
        channel_show = create_random_channel_show(
            session,
            channel,
            source,
            is_whitelist=False,
        )
        create_random_episode(
            session,
            channel_show_show(session, channel_show),
            canonical_episode_id=shared_episode.id,
        )
        shows[key] = channel_show_show(session, channel_show)
    return channel, shows


# TODO: Validate
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


# TODO: Validate
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


# TODO: Validate
def test_duplicate_episode_collapses_to_priority_source(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    channel, shows = _build_duplicated_channel(session_scoped_session, user)

    # Prioritize SOURCE_KEY_B over SOURCE_KEY_A.
    _set_preferences(
        session_scoped_session,
        user,
        [
            SourcePreference(source_key=SOURCE_KEY_B, enabled=True),
            SourcePreference(source_key=SOURCE_KEY_A, enabled=True),
        ],
    )

    show_ids = _selected_show_ids(session_scoped_session, channel, user)

    assert show_ids == [shows[SOURCE_KEY_B].id]


# TODO: Validate
def test_disabled_source_is_hidden_globally(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    channel, shows = _build_duplicated_channel(session_scoped_session, user)

    # SOURCE_KEY_B is the higher priority but globally disabled, so
    # SOURCE_KEY_A wins instead.
    _set_preferences(
        session_scoped_session,
        user,
        [
            SourcePreference(source_key=SOURCE_KEY_B, enabled=False),
            SourcePreference(source_key=SOURCE_KEY_A, enabled=True),
        ],
    )

    show_ids = _selected_show_ids(session_scoped_session, channel, user)

    assert show_ids == [shows[SOURCE_KEY_A].id]


# TODO: Validate
def test_channel_source_filter_stacks_on_top_of_preferences(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    channel, shows = _build_duplicated_channel(session_scoped_session, user)

    # Globally SOURCE_KEY_B wins, but the channel blacklists its source, so the
    # per-channel filter narrows the result to SOURCE_KEY_A.
    _set_preferences(
        session_scoped_session,
        user,
        [
            SourcePreference(source_key=SOURCE_KEY_B, enabled=True),
            SourcePreference(source_key=SOURCE_KEY_A, enabled=True),
        ],
    )
    options = ChannelOptions(
        source_ids=[shows[SOURCE_KEY_B].source_id],
        source_ids_is_blacklist=True,
    )

    show_ids = _selected_show_ids(session_scoped_session, channel, user, options)

    assert show_ids == [shows[SOURCE_KEY_A].id]
