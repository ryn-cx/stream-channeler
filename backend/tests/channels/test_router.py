# TODO: Validate
import json
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import ChannelShow
from app.channels.schemas import (
    ChannelInput,
    ChannelOutput,
    MultipleChannelQueueOutputs,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.config import settings
from app.media.models import Episode, Plugin
from tests.utils.channel import (
    RandomChannel,
    add_urls_to_channel_queue_api,
    create_channel_api,
    delete_channel_api,
    delete_channel_queue_url_api,
    get_channel_api,
    get_channel_episodes_api,
    get_channel_queue_api,
    get_channels_api,
    update_channel_api,
)
from tests.utils.media import create_random_heirarchy
from tests.utils.test_assertions import (
    assert_not_authenticated,
    assert_not_enough_permission,
    assert_not_found,
)
from tests.utils.user import CreatedUser, create_user_api
from tests.utils.utils import random_bool, random_lower_string

# ---------------------------------------------------------------------------
# Test setup helpers
# ---------------------------------------------------------------------------


def generic_channel_tester(
    client: TestClient,
    channel_owner: CreatedUser | None = None,
    accessing_user: CreatedUser | None = None,
    *,
    public: bool,
) -> None:
    channel_owner = channel_owner or create_user_api(client)

    # Do the test twice, once to test the DB when it has 1 entry, and again to test it
    # when it has multiple entries
    for _ in range(2):
        random_channel = RandomChannel(public=public)
        channel = create_channel_api(client, channel_owner, random_channel)
        response = get_channel_api(client, channel.id, accessing_user)
        assert response == channel


def get_channels_tester(
    client: TestClient,
    accessing_user: CreatedUser,
    channel_owner: CreatedUser | None = None,
) -> None:
    channel_owner = channel_owner or create_user_api(client)
    channels: list[ChannelOutput] = []
    # Test reading 0 channels, 1 channel, and multiple channels.
    for _ in range(3):
        get_channels_api(client, accessing_user, expected_output=channels)
        response = create_channel_api(client, channel_owner)
        channels.append(response)


def set_channel_show_whitelist_api(
    client: TestClient,
    channel_show: ChannelShow,
    random_user: CreatedUser,
    whitelist_config: WhitelistShowInput | WhitelistShowOutput,
) -> WhitelistShowOutput:
    response = client.post(
        f"{settings.API_V1_STR}/channels/{channel_show.channel_id}/whitelist/{channel_show.show_id}",
        headers=random_user.headers,
        # model_dump_json will convert UUIDs into strings and json.loads will recreate
        # the structure required for the json parameter.
        json=json.loads(whitelist_config.model_dump_json()),
    )
    assert response.status_code == status.HTTP_200_OK
    return WhitelistShowOutput.model_validate(response.json())


def get_channel_show_whitelist_api(
    client: TestClient,
    channel_show: ChannelShow,
    random_user: CreatedUser,
    expected_output: WhitelistShowInput | None = None,
) -> WhitelistShowOutput:
    response = client.get(
        f"{settings.API_V1_STR}/channels/{channel_show.channel_id}/whitelist/{channel_show.show_id}",
        headers=random_user.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    output = WhitelistShowOutput.model_validate(response.json())

    if isinstance(expected_output, WhitelistShowInput):
        assert expected_output == WhitelistShowInput.model_validate(output)

    return output


def create_channel_show(
    db: Session,
    plugin: list[Plugin],
    channel: ChannelOutput,
    whitelist_mode: bool | None = None,  # noqa: FBT001
) -> ChannelShow:
    channel_show = ChannelShow(
        channel_id=channel.id,
        show_id=plugin[0].sources[0].shows[0].id,
        white_list_mode=whitelist_mode if whitelist_mode is not None else random_bool(),
    )
    db.add(channel_show)
    db.commit()
    return channel_show


def create_channel_show_whitelist(
    client: TestClient,
    user: CreatedUser,
    channel_show: ChannelShow,
    blank_whitelist: WhitelistShowOutput,
) -> None:
    # Alternate the whitelist status of each entry to make sure every possible value
    # gets tested.
    season_alternator = False
    for season in blank_whitelist.seasons:
        season_alternator = season.enabled = not season_alternator

        episode_alternator = False
        for episode in season.episodes:
            episode_alternator = episode.enabled = not episode_alternator

    set_channel_show_whitelist_api(client, channel_show, user, blank_whitelist)


def initialize_whitelist_data(
    client: TestClient,
    db: Session,
    user: CreatedUser | None = None,
    count: int = 4,
    whitelist_mode: bool | None = None,  # noqa: FBT001
) -> ChannelShow:
    """Create a ChannelShow with a whitelist configuration."""
    user = user or create_user_api(client)
    channel = create_channel_api(client, user)
    plugin = create_random_heirarchy(db, season_count=count, episode_count=count)
    channel_show = create_channel_show(db, plugin, channel, whitelist_mode)
    blank_whitelist = get_channel_show_whitelist_api(client, channel_show, user)
    create_channel_show_whitelist(client, user, channel_show, blank_whitelist)

    return channel_show


# ---------------------------------------------------------------------------
# Channel Create Tests
# ---------------------------------------------------------------------------


def test_create_channels(client: TestClient) -> None:
    random_user = create_user_api(client)
    channels: list[ChannelOutput] = []
    # Test adding to an empty channel list, a channel list with one channel, and a
    # channel list with multiple channels.
    for _ in range(3):
        random_channel = RandomChannel()
        response = create_channel_api(
            client,
            random_user,
            random_channel,
            random_channel,
        )

        channels.append(response)
        # Make sure the entry is actually added to the database
        get_channels_api(client, random_user, expected_output=channels)


def test_create_channel_no_account(client: TestClient) -> None:
    assert_not_authenticated(client, "post", f"{settings.API_V1_STR}/channels/")


# TODO: Generalized conflict assertion like assert_not_authenticated?
def test_create_channel_already_exists(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = client.post(
        url=f"{settings.API_V1_STR}/channels/",
        headers=random_user.headers,
        json=ChannelInput.model_validate(channel).model_dump(),
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    content = response.json()
    assert content["detail"] == "Channel with this name already exists"


# ---------------------------------------------------------------------------
# Channel Get (Single) Tests
# ---------------------------------------------------------------------------


def test_get_own_private_channel(client: TestClient) -> None:
    random_user = create_user_api(client)
    generic_channel_tester(client, random_user, random_user, public=False)


def test_get_own_public_channel(client: TestClient) -> None:
    random_user = create_user_api(client)
    generic_channel_tester(client, random_user, random_user, public=True)


# TODO: Add superuser tests to other end points
def test_get_private_channel_as_superuser(
    client: TestClient,
    super_user: CreatedUser,
) -> None:
    generic_channel_tester(client, accessing_user=super_user, public=False)


def test_get_public_channel_no_user(client: TestClient) -> None:
    generic_channel_tester(client, accessing_user=None, public=True)


def test_get_public_channel_wrong_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    generic_channel_tester(client, accessing_user=random_user, public=True)


def test_get_channel_not_found(client: TestClient) -> None:
    random_user = create_user_api(client)

    assert_not_found(
        client=client,
        method="get",
        url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}",
        detail="Channel not found",
        headers=random_user.headers,
    )


def test_get_private_channel_wrong_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_channel=RandomChannel(public=False))
    assert_not_enough_permission(
        client,
        "get",
        f"{settings.API_V1_STR}/channels/{channel.id}",
        random_user,
    )


def test_get_private_channel_no_user(client: TestClient) -> None:
    channel = create_channel_api(client, random_channel=RandomChannel(public=False))
    assert_not_authenticated(
        client,
        "get",
        f"{settings.API_V1_STR}/channels/{channel.id}",
    )


# ---------------------------------------------------------------------------
# Channel Get (Multiple) Tests
# ---------------------------------------------------------------------------


def test_get_channels(client: TestClient) -> None:
    random_user = create_user_api(client)
    get_channels_tester(client, accessing_user=random_user, channel_owner=random_user)


def test_get_channels_as_superuser(
    client: TestClient,
    super_user: CreatedUser,
) -> None:
    get_channels_tester(client, accessing_user=super_user)


def test_read_channels_no_user(client: TestClient) -> None:
    assert_not_authenticated(client, "get", f"{settings.API_V1_STR}/channels/")


def test_get_channels_pagination(
    client: TestClient,
) -> None:
    random_user = create_user_api(client)
    total_channels = 150
    channels = [create_channel_api(client, random_user) for _ in range(total_channels)]
    get_channels_api(client, random_user, expected_output=channels)


# ---------------------------------------------------------------------------
# Channel Update Tests
# ---------------------------------------------------------------------------


def test_update_channel(client: TestClient) -> None:
    channels: list[ChannelOutput] = []
    for _ in range(3):
        random_user = create_user_api(client)
        channel = create_channel_api(client, random_user)
        new_data = RandomChannel().model_dump()
        expected_response = ChannelOutput(
            **new_data,
            id=channel.id,
            user_id=random_user.id,
        )

        update_channel_api(
            client=client,
            channel_id=channel.id,
            user=random_user,
            update_data=new_data,
            expected_output=expected_response,
        )
        channels.append(expected_response)

        # Make sure the data is actually updated in the database
        get_channels_api(client, random_user, expected_output=channels)


# TODO: Special conflict function
def test_rename_channel_name_already_exists(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    channel2 = create_channel_api(client, random_user)

    response = client.put(
        url=f"{settings.API_V1_STR}/channels/{channel2.id}",
        headers=random_user.headers,
        json=RandomChannel(name=channel.name).model_dump(),
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Channel with this name already exists"

    # Make sure the channel was not modified
    get_channels_api(client, random_user, expected_output=[channel, channel2])


def test_channel_update_not_found(client: TestClient) -> None:
    random_user = create_user_api(client)
    assert_not_found(
        client=client,
        method="put",
        url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}",
        detail="Channel not found",
        headers=random_user.headers,
        parameters=RandomChannel().model_dump(),
    )

    # Make sure the channel was not created
    get_channels_api(client, random_user, expected_output=[])


def test_update_channel_wrong_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    original_user = create_user_api(client)
    channel = create_channel_api(client, original_user)
    assert_not_enough_permission(
        client=client,
        method="put",
        url=f"{settings.API_V1_STR}/channels/{channel.id}",
        user=random_user,
        parameters=RandomChannel().model_dump(),
    )

    # Make sure the channel was not modified
    get_channels_api(client, original_user, expected_output=[channel])


def test_update_channel_no_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    assert_not_authenticated(
        client=client,
        method="put",
        url=f"{settings.API_V1_STR}/channels/{channel.id}",
        parameters=RandomChannel().model_dump(),
    )

    # Make sure the channel was not modified
    get_channels_api(client, random_user, expected_output=[channel])


# ---------------------------------------------------------------------------
# Channel Delete Tests
# ---------------------------------------------------------------------------


def test_delete_channel(client: TestClient) -> None:
    random_user = create_user_api(client)
    channels: list[ChannelOutput] = []
    # Test deleting when there are 0 channels, 1 channel, and multiple channels.
    for _ in range(3):
        response = create_channel_api(client, random_user)
        channels.append(response)

    for i, channel in enumerate(channels):
        response = delete_channel_api(client, channel.id, random_user)

        get_channels_api(client, random_user, expected_output=channels[i + 1 :])


def test_delete_channel_not_found(client: TestClient) -> None:
    random_user = create_user_api(client)
    assert_not_found(
        client,
        "delete",
        f"{settings.API_V1_STR}/channels/{uuid.uuid4()}",
        "Channel not found",
        random_user.headers,
    )


def test_delete_channel_wrong_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    assert_not_enough_permission(
        client,
        "delete",
        f"{settings.API_V1_STR}/channels/{channel.id}",
        create_user_api(client),
    )

    # Make sure channel still exists
    get_channels_api(client, random_user, expected_output=[channel])


def test_delete_channel_no_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    assert_not_authenticated(
        client,
        "delete",
        f"{settings.API_V1_STR}/channels/{channel.id}",
    )

    # Make sure channel still exists
    get_channels_api(client, random_user, expected_output=[channel])


# ---------------------------------------------------------------------------
# Episode Tests
# ---------------------------------------------------------------------------


def test_get_channel_with_episodes(client: TestClient, db: Session) -> None:
    random_user = create_user_api(client)

    channel = create_channel_api(client, random_user)
    plugins = create_random_heirarchy(db, default_count=2)

    episodes: list[Episode] = []
    for plugin in plugins:
        for source in plugin.sources:
            for show in source.shows:
                channel_show = ChannelShow(
                    channel_id=channel.id,
                    show_id=show.id,
                    white_list_mode=False,
                )
                db.add(channel_show)
                for season in show.seasons:
                    episodes.extend(season.episodes)

    db.commit()
    get_channel_episodes_api(client, random_user, channel, episodes)


def test_get_channel_with_no_episodes(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    get_channel_episodes_api(client, random_user, channel, [])


def test_get_channel_episodes_no_user(
    client: TestClient,
) -> None:
    channel = create_channel_api(client, random_channel=RandomChannel(public=False))

    assert_not_authenticated(
        client,
        "get",
        f"{settings.API_V1_STR}/channels/{channel.id}/episodes",
    )


def test_get_channel_episodes_wrong_user(
    client: TestClient,
) -> None:
    channel = create_channel_api(client, random_channel=RandomChannel(public=False))

    assert_not_enough_permission(
        client,
        "get",
        f"{settings.API_V1_STR}/channels/{channel.id}/episodes",
        create_user_api(client),
    )


# ---------------------------------------------------------------------------
# Queue Add URL Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("initial_url_count", "new_url_count"),
    [(i, j) for i in range(3) for j in range(3)],
)
def test_append_urls_to_queue(
    client: TestClient,
    initial_url_count: int,
    new_url_count: int,
) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)

    # Test adding URLs to a queueu with 0 URLs, 1 URL, and multiple URLs.
    # TODO: Verify the response
    response = add_urls_to_channel_queue_api(
        client,
        channel,
        random_user,
        [random_lower_string() for _ in range(initial_url_count)],
    )
    response.data = response.data[::-1]

    # Test adding 0 URLs, 1 URL, and multiple URLs to the queue at once.
    # TODO: Verify the response
    response_2 = add_urls_to_channel_queue_api(
        client,
        channel,
        random_user,
        [random_lower_string() for _ in range(new_url_count)],
    )

    response_2.data = response_2.data[::-1]

    expected_response = MultipleChannelQueueOutputs(
        data=response_2.data + response.data,
        count=response_2.count + response.count,
    )

    get_channel_queue_api(client, random_user, channel, expected_response)


def test_append_existing_url(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    first_url = random_lower_string()
    add_urls_to_channel_queue_api(client, channel, random_user, [first_url])

    response = add_urls_to_channel_queue_api(client, channel, random_user, [first_url])

    get_channel_queue_api(client, random_user, channel, response)


def test_append_duplicate_urls(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    random_url = random_lower_string()

    response = add_urls_to_channel_queue_api(
        client,
        channel,
        random_user,
        [random_url, random_url],
    )

    response.data = response.data[::-1]

    get_channel_queue_api(client, random_user, channel, response)


def test_append_urls_to_channel_no_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = add_urls_to_channel_queue_api(client, channel, random_user)

    assert_not_authenticated(
        client=client,
        method="post",
        url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
        parameters=[random_lower_string()],
    )

    # Make sure the channel queue is unchanged
    get_channel_queue_api(client, random_user, channel, response)


def test_append_urls_to_channel_wrong_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = add_urls_to_channel_queue_api(client, channel, random_user)

    assert_not_enough_permission(
        client=client,
        method="post",
        url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
        user=create_user_api(client),
        parameters=[random_lower_string()],
    )

    # Make sure the channel queue is unchanged
    get_channel_queue_api(client, random_user, channel, response)


# ---------------------------------------------------------------------------
# Queue Delete URL Tests
# ---------------------------------------------------------------------------


def test_delete_url_in_queue(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = add_urls_to_channel_queue_api(
        client,
        channel,
        random_user,
        [random_lower_string() for _ in range(4)],
    )

    response_clone = response.model_copy()
    response.data = response.data[::-1]

    for queue_entry in response_clone.data:
        delete_channel_queue_url_api(
            client,
            random_user,
            channel,
            queue_entry,
        )
        response.data.pop()
        response.count -= 1

    get_channel_queue_api(client, random_user, channel, response)


def test_delete_invalid_url(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = add_urls_to_channel_queue_api(client, channel, random_user)

    assert_not_found(
        client=client,
        method="delete",
        url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{uuid.uuid4()}",
        headers=random_user.headers,
        detail="URL not found",
    )

    # Make sure the channel queue is unchanged
    get_channel_queue_api(client, random_user, channel, response)


def test_delete_from_queue_no_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = add_urls_to_channel_queue_api(client, channel, random_user)

    assert_not_authenticated(
        client=client,
        method="delete",
        url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{response.data[0].id}",
    )

    # Make sure the channel queue is unchanged
    get_channel_queue_api(client, random_user, channel, response)


def test_delete_from_queue_wrong_user(client: TestClient) -> None:
    random_user = create_user_api(client)
    channel = create_channel_api(client, random_user)
    response = add_urls_to_channel_queue_api(client, channel, random_user)

    assert_not_enough_permission(
        client=client,
        method="delete",
        url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{response.data[0].id}",
        user=create_user_api(client),
    )

    # Make sure the channel queue is unchanged
    get_channel_queue_api(client, random_user, channel, response)


# ---------------------------------------------------------------------------
# Whitelist Tests
# ---------------------------------------------------------------------------


def test_get_channel_show_whitelist(client: TestClient, db: Session) -> None:
    random_user = create_user_api(client)
    channel_show = initialize_whitelist_data(client, db, random_user)
    response = get_channel_show_whitelist_api(client, channel_show, random_user)

    whitelist_input = WhitelistShowInput.model_validate(response)

    season_alternator = False
    for season in whitelist_input.seasons:
        season_alternator = not season_alternator
        assert season.enabled == season_alternator

        episode_alternator = False
        for episode in season.episodes:
            episode_alternator = not episode_alternator
            assert episode.enabled == episode_alternator


def test_set_channel_show_whitelist(client: TestClient, db: Session) -> None:
    random_user = create_user_api(client)
    channel_show = initialize_whitelist_data(client, db, random_user)
    response = get_channel_show_whitelist_api(client, channel_show, random_user)

    whitelist_input = WhitelistShowInput.model_validate(response)
    # 4 different state combinations need to be tested
    # - enabled -> disabled
    # - disabled -> enabled
    # - enabled -> enabled
    # - disabled -> disabled
    # initialize_whitelist_data will rotate the values with the first value being
    # enabled, second value being disabled etc. If the first 2 values are inverted then
    # every possible combination will be tested and match the order in the list.
    whitelist_input.seasons[0].enabled = not whitelist_input.seasons[0].enabled
    whitelist_input.seasons[1].enabled = not whitelist_input.seasons[1].enabled
    for season in whitelist_input.seasons:
        season.episodes[0].enabled = not season.episodes[0].enabled
        season.episodes[1].enabled = not season.episodes[1].enabled

    response = set_channel_show_whitelist_api(
        client,
        channel_show,
        random_user,
        whitelist_input,
    )
    assert whitelist_input == WhitelistShowInput.model_validate(response)

    get_channel_show_whitelist_api(client, channel_show, random_user, whitelist_input)


def test_get_channel_show_whitelist_no_user(db: Session, client: TestClient) -> None:
    channel_show = initialize_whitelist_data(client, db)

    assert_not_authenticated(
        client=client,
        method="get",
        url=f"{settings.API_V1_STR}/channels/{channel_show.channel_id}/whitelist/{channel_show.show_id}",
    )


def test_set_channel_show_whitelist_no_user(
    db: Session,
    client: TestClient,
) -> None:
    random_user = create_user_api(client)
    channel_show = initialize_whitelist_data(client, db, random_user)

    response = get_channel_show_whitelist_api(client, channel_show, random_user)

    whitelist_input = WhitelistShowInput.model_validate(response)
    for season in whitelist_input.seasons:
        season.enabled = random_bool()
        for episode in season.episodes:
            episode.enabled = random_bool()

    assert_not_authenticated(
        client=client,
        method="post",
        url=f"{settings.API_V1_STR}/channels/{channel_show.channel_id}/whitelist/{channel_show.show_id}",
        parameters=json.loads(whitelist_input.model_dump_json()),
    )


def test_set_channel_show_whitelist_bypass_attempt(
    db: Session,
    client: TestClient,
) -> None:
    random_user = create_user_api(client)
    random_user_2 = create_user_api(client)

    channel_show = initialize_whitelist_data(client, db, random_user)
    channel_show_2 = initialize_whitelist_data(client, db, random_user_2)

    channel_2 = create_channel_api(client, random_user_2)
    db.add(channel_show_2)
    db.commit()

    response = get_channel_show_whitelist_api(client, channel_show_2, random_user_2)

    whitelist_input = WhitelistShowInput.model_validate(response)

    assert_not_found(
        client=client,
        method="post",
        url=f"{settings.API_V1_STR}/channels/{channel_2.id}/whitelist/{channel_show.id}",
        detail="Show was not found on channel",
        headers=random_user_2.headers,
        parameters=json.loads(whitelist_input.model_dump_json()),
    )
