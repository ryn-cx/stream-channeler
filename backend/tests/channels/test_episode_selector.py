# TODO: Validate
from uuid import UUID

from sqlmodel import Session

from app.channels.episode_selector import EpisodeQueryBuilder
from app.channels.models import Channel, ChannelShow
from app.channels.schemas import ChannelMediaFilter
from app.media.models import Episode
from tests.utils.media import create_random_heirarchy
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def test_episode_query_builder_rotate_shows_sort_and_order(db: Session) -> None:
    # Create a user and channel
    created_user = create_random_user(db=db)
    channel = Channel(name=random_lower_string(), user_id=created_user.id)
    db.add(channel)

    plugins = create_random_heirarchy(
        db,
        plugin_count=1,
        source_count=1,
        show_count=5,
        season_count=5,
        episode_count=5,
    )

    plugin = plugins[0]

    # Add all shows to the channel
    for show in plugin.sources[0].shows:
        channel_show = ChannelShow(
            channel_id=channel.id,
            show_id=show.id,
            white_list_mode=False,
        )
        db.add(channel_show)

    db.commit()

    media_filter = ChannelMediaFilter(
        sort_by=[
            "value.episode.episode_number.ascending",
            "sum.show-episodes.duration.descending",
        ],
        rotate_shows=True,
    )

    builder = EpisodeQueryBuilder(db, channel, media_filter)
    episodes = builder.get_episodes()

    episodes_by_show: dict[UUID, list[Episode]] = {}
    for episode in episodes:
        episodes_by_show.setdefault(episode.season.show_id, []).append(episode)

    # Validate that the episodes are ordered by the episode_number
    for show_id, episodes in episodes_by_show.items():
        episode_numbers = [e.episode_number for e in episodes if e.episode_number]
        assert episode_numbers == sorted(episode_numbers), (
            f"Episodes for show {show_id} are not ordered by episode_number ascending"
        )

    # TODO: BELOW THIS IS WACK
    # Compile show durations in a seperate loop to make test easier to follow.
    show_durations: list[tuple[UUID, int]] = []
    for show_id, episodes in episodes_by_show.items():
        total = sum(e.duration or 0 for e in episodes)
        show_durations.append((show_id, total))

    # Validate that shows appear in descending order of total duration
    # When rotate_shows=True with secondary sort by total duration descending,
    # the first occurrence of each show should be in descending order by total
    totals_only = [total for _, total in show_durations]
    assert totals_only == sorted(totals_only, reverse=True), (
        f"Shows are not ordered by descending total duration. Got: {totals_only}, "
        f"Expected: {sorted(totals_only, reverse=True)}"
    )
