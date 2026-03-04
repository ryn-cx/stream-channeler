# TODO: Validate
import uuid

from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.channels.models import (
    ChannelEpisodeWhiteList,
    ChannelSeasonWhiteList,
    ChannelShow,
)
from app.channels.schemas import ChannelOutput

# from app.channels.service import get_episodes
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.watches.models import Watch
from tests.old_tests.utils.channel import create_channel_api
from tests.users.utils import CreatedUser
from tests.utils.media import create_random_heirarchy
from tests.utils.utils import random_bool


class Whitelists(BaseModel):
    listed_seasons: list[Season]
    listed_episodes: list[Episode]
    unlisted_seasons: list[Season]
    unlisted_episodes: list[Episode]


class WatchLists(BaseModel):
    watched_episodes: list[Episode] = Field(default=[])
    unwatched_episodes: list[Episode] = Field(default=[])


class CombinedLists(Whitelists, WatchLists):
    channel_id: uuid.UUID


def add_shows_to_channel(
    db: Session,
    channel: ChannelOutput,
    plugins: list[Plugin],
    *,
    whitelist_mode: bool,
) -> None:
    for plugin in plugins:
        for source in plugin.sources:
            for show in source.shows:
                channel_show = ChannelShow(
                    channel_id=channel.id,
                    show_id=show.id,
                    white_list_mode=whitelist_mode,
                )
                db.add(channel_show)


def create_random_whitelist_entries(
    db: Session,
    channel: ChannelOutput,
    plugins: list[Plugin],
) -> Whitelists:
    listed_seasons: list[Season] = []
    unlisted_seasons: list[Season] = []
    listed_episodes: list[Episode] = []
    unlisted_episodes: list[Episode] = []
    for plugin in plugins:
        for source in plugin.sources:
            for show in source.shows:
                statement = select(ChannelShow).where(
                    ChannelShow.channel_id == channel.id,
                    ChannelShow.show_id == show.id,
                )
                channel_show = db.exec(statement).one()

                for season in show.seasons:
                    if random_bool():
                        channel_season = ChannelSeasonWhiteList(
                            channel_show_id=channel_show.id,
                            season_id=season.id,
                        )
                        db.add(channel_season)
                        listed_seasons.append(season)
                    else:
                        unlisted_seasons.append(season)

                    for episode in season.episodes:
                        if random_bool():
                            channel_episode = ChannelEpisodeWhiteList(
                                channel_show_id=channel_show.id,
                                episode_id=episode.id,
                            )
                            db.add(channel_episode)
                            listed_episodes.append(episode)
                        else:
                            unlisted_episodes.append(episode)
    return Whitelists(
        listed_seasons=listed_seasons,
        listed_episodes=listed_episodes,
        unlisted_seasons=unlisted_seasons,
        unlisted_episodes=unlisted_episodes,
    )


def create_random_watch_entries(
    db: Session,
    user: CreatedUser,
    plugins: list[Plugin],
) -> WatchLists:
    unwatched_episodes: list[Episode] = []
    watched_episodes: list[Episode] = []
    for plugin in plugins:
        for source in plugin.sources:
            for show in source.shows:
                for season in show.seasons:
                    for episode in season.episodes:
                        if random_bool():
                            watch_entry = Watch(
                                user_id=user.id,
                                episode_id=episode.id,
                                verified=True,
                            )
                            watched_episodes.append(episode)
                            db.add(watch_entry)
                        else:
                            unwatched_episodes.append(episode)
    return WatchLists(
        watched_episodes=watched_episodes,
        unwatched_episodes=unwatched_episodes,
    )


def whitelist_mode_episodes(lists: Whitelists) -> list[Episode]:
    all_episodes: list[Episode] = []
    # If the season is listed every episode for that season should be listed too.
    for season in lists.listed_seasons:
        all_episodes.extend(season.episodes)

    # If the episode is listed it should be included too.
    for episode in lists.listed_episodes:
        if episode not in all_episodes:
            all_episodes.append(episode)

    return all_episodes


def blacklist_mode_episodes(lists: Whitelists) -> list[Episode]:
    all_episodes: list[Episode] = []
    # Only include episodes that are unlisted in both the season and the episode list.
    for season in lists.unlisted_seasons:
        for episode in season.episodes:
            if episode not in all_episodes and episode not in lists.listed_episodes:
                all_episodes.append(episode)

    return all_episodes


def generate_test_data(
    client: TestClient,
    db: Session,
    random_user: CreatedUser,
    number_of_entries: int = 3,
    *,
    whitelist_mode: bool = True,
) -> CombinedLists:
    channel = create_channel_api(client, random_user)
    plugins = create_random_heirarchy(db, default_count=number_of_entries)
    add_shows_to_channel(db, channel, plugins, whitelist_mode=whitelist_mode)
    whitelist = create_random_whitelist_entries(db, channel, plugins)
    watchlist = create_random_watch_entries(db, random_user, plugins)
    # Do not use model_dump() because children will be lost
    return CombinedLists(
        channel_id=channel.id,
        listed_seasons=whitelist.listed_seasons,
        listed_episodes=whitelist.listed_episodes,
        unlisted_seasons=whitelist.unlisted_seasons,
        unlisted_episodes=whitelist.unlisted_episodes,
        watched_episodes=watchlist.watched_episodes,
        unwatched_episodes=watchlist.unwatched_episodes,
    )


def check_episodes(
    episodes: list[Episode],
    listed_episodes: list[Episode],
) -> None:
    listed_episodes.sort(key=lambda e: str(e.id))
    episodes.sort(key=lambda e: str(e.id))

    listed_episode_keys = [e.id for e in listed_episodes]
    episode_keys = [e.id for e in episodes]

    listed_episode_keys.sort(key=lambda e: str(e))
    episode_keys.sort(key=lambda e: str(e))
    assert set(listed_episode_keys) == set(episode_keys)


# def test_get_episodes_whitelist(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(),
#     )
#     episodes = list(episodes)

#     check_episodes(episodes, whitelist_mode_episodes(lists))


# def test_get_episodes_blacklist(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user, whitelist_mode=False)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(),
#     )
#     episodes = list(episodes)
#     check_episodes(episodes, blacklist_mode_episodes(lists))


# # TODO: test_get_episodes_hide_unwatched
# def test_get_episodes_hide_watched(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(hide_watched=True),
#         random_user,
#     )
#     episodes = list(episodes)

#     whitelist = whitelist_mode_episodes(lists)
#     unwatched_list = lists.unwatched_episodes
#     expected = [x for x in unwatched_list if x in whitelist]

#     check_episodes(episodes, expected)


# def test_get_episodes_sorted_by_episode(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user, whitelist_mode=False)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(sort_by=["episode.name"]),
#     )

#     last_episode_name = episodes[0].name
#     for episode in episodes[1:]:
#         if episode.name and last_episode_name:
#             assert last_episode_name <= episode.name
#             last_episode_name = episode.name


# def test_get_episodes_sorted_by_season(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user, whitelist_mode=False)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(sort_by=["season.name"]),
#     )

#     last_season_name = episodes[0].season.name
#     for episode in episodes[1:]:
#         current_season_name = episode.season.name
#         # When a None value is found, all later values should also be None
#         if last_season_name is None:
#             assert current_season_name is None
#         elif current_season_name is not None:
#             assert last_season_name <= current_season_name
#         last_season_name = current_season_name


# def test_get_episodes_sorted_by_show_name(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user, whitelist_mode=False)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(sort_by=["show.name.asc"]),
#     )

#     last_show_name = episodes[0].season.show.name
#     for episode in episodes[1:]:
#         assert last_show_name <= episode.season.show.name
#         last_show_name = episode.season.show.name


# def show_season_episode_string(episodes: Episode) -> str:
#     output = ""
#     output += str(episodes.season.show.name) + " "
#     # Silly workaround for the fact that season names can be blank
#     output += str(episodes.season.name or "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz") + " "
#     output += str(episodes.name) + " "
#     return output


# def test_get_episodes_sorted_by_show_season_name(
#     client: TestClient,
#     db: Session,
# ) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user, whitelist_mode=False)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(
#             sort_by=["show.name.asc", "season.name.asc", "episode.name.asc"],
#         ),
#     )

#     last_name = show_season_episode_string(episodes[0])
#     for episode in episodes[1:]:
#         assert last_name <= show_season_episode_string(episode)
#         last_name = show_season_episode_string(episode)


# def test_rotate_shows(client: TestClient, db: Session) -> None:
#     random_user = create_user_api(client, db)
#     lists = generate_test_data(client, db, random_user, whitelist_mode=False)

#     episodes = get_episodes(
#         db,
#         db.get_one(Channel, lists.channel_id),
#         ChannelMediaFilter(rotate_shows=True),
#     )

#     last_show = episodes[0].season.show.name
#     all_should_match = False
#     for episode in episodes[1:]:
#         if all_should_match:
#             assert last_show == episode.season.show.name
#         elif last_show == episode.season.show.name:
#             all_should_match = True
#         else:
#             assert last_show != episode.season.show.name

#         last_show = episode.season.show.name
