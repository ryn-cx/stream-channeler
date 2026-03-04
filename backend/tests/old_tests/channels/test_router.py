# TODO: Validate
import json
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.channels.models import Channel, ChannelShow
from app.channels.schemas import (
    ChannelInput,
    ChannelOutput,
    MultipleChannelOutputs,
    MultipleChannelQueueOutputs,
    WhitelistEpisodeInput,
    WhitelistSeasonInput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import Plugin
from tests.old_tests.utils.channel import (
    add_urls_to_channel_queue_api,
    create_channel_api,
    delete_channel_queue_url_api,
    get_channel_api,
    get_channel_episodes_api,
    get_channel_queue_api,
    get_channels_api,
)
from tests.old_tests.utils.media import (
    create_random_heirarchy,
)
from tests.old_tests.utils.test_assertions import (
    assert_conflict,
    assert_delete,
    assert_not_authenticated,
    assert_not_enough_permission,
    assert_not_found,
    assert_saved_to_db,
    assert_success,
)
from tests.old_tests.utils.user import CreatedUser, create_random_user_alt
from tests.old_tests.utils.utils import (
    dump_random_model,
    random_bool,
    random_lower_string,
)

# region Whitelist Helpers


def whitelist_output_to_input(output: WhitelistShowOutput) -> WhitelistShowInput:
    return WhitelistShowInput(
        id=output.id,
        whitelist_mode=output.whitelist_mode,
        seasons=[
            WhitelistSeasonInput(
                id=season.id,
                enabled=season.id in output.enabled_season_ids,
                episodes=[
                    WhitelistEpisodeInput(
                        id=episode.id,
                        enabled=episode.id in output.enabled_episode_ids,
                    )
                    for episode in output.episodes
                    if episode.season_id == season.id
                ],
            )
            for season in output.seasons
        ],
    )


def set_channel_show_whitelist_api(
    client: TestClient,
    channel_show: ChannelShow,
    random_user: CreatedUser,
    whitelist_config: WhitelistShowInput | WhitelistShowOutput,
) -> WhitelistShowOutput:
    response = client.post(
        f"{settings.API_V1_STR}/channels/{channel_show.channel_id}/whitelist/{channel_show.show_id}",
        headers=random_user.headers,
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
        assert expected_output == whitelist_output_to_input(output)

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
    whitelist_seasons: list[WhitelistSeasonInput] = []
    for season in blank_whitelist.seasons:
        season_alternator = not season_alternator

        episode_alternator = False
        whitelist_episodes: list[WhitelistEpisodeInput] = []
        for episode in blank_whitelist.episodes:
            if episode.season_id == season.id:
                episode_alternator = not episode_alternator
                whitelist_episodes.append(
                    WhitelistEpisodeInput(id=episode.id, enabled=episode_alternator),
                )

        whitelist_seasons.append(
            WhitelistSeasonInput(
                id=season.id,
                enabled=season_alternator,
                episodes=whitelist_episodes,
            ),
        )

    whitelist_input = WhitelistShowInput(
        id=blank_whitelist.id,
        whitelist_mode=blank_whitelist.whitelist_mode,
        seasons=whitelist_seasons,
    )
    set_channel_show_whitelist_api(client, channel_show, user, whitelist_input)


def initialize_whitelist_data(
    client: TestClient,
    db: Session,
    user: CreatedUser | None = None,
    count: int = 4,
    whitelist_mode: bool | None = None,  # noqa: FBT001
) -> ChannelShow:
    """Create a ChannelShow with a whitelist configuration."""
    user = user or create_random_user_alt(client, db)
    channel = create_channel_api(client, user)
    plugin = create_random_heirarchy(db, season_count=count, episode_count=count)
    channel_show = create_channel_show(db, plugin, channel, whitelist_mode)
    blank_whitelist = get_channel_show_whitelist_api(client, channel_show, user)
    create_channel_show_whitelist(client, user, channel_show, blank_whitelist)

    return channel_show


# endregion


class TestCreateChannel:
    def test_create_channel(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput)

        content = assert_success(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/channels/",
            output_model=ChannelOutput,
            headers=user.headers,
            parameters=data,
        )
        assert_saved_to_db(db, Channel, content.id, data)

    def test_create_channel_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        data = dump_random_model(ChannelInput)
        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/channels/",
            parameters=data,
        )
        assert not db.exec(select(Channel).where(Channel.name == data["name"])).first()


class TestGetChannel:
    def test_get_own_private_channel(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=False)
        channel = create_channel_api(client, user, data)
        response = get_channel_api(client, channel.id, user)
        assert response == channel

    def test_get_own_public_channel(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=True)
        channel = create_channel_api(client, user, data)
        response = get_channel_api(client, channel.id, user)
        assert response == channel

    def test_get_private_channel_as_superuser(
        self,
        client: TestClient,
        db: Session,
        super_user: CreatedUser,
    ) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=False)
        channel = create_channel_api(client, user, data)
        response = get_channel_api(client, channel.id, super_user)
        assert response == channel

    def test_get_public_channel_no_user(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=True)
        channel = create_channel_api(client, user, data)

        response = client.get(f"{settings.API_V1_STR}/channels/{channel.id}")
        assert response.status_code == status.HTTP_200_OK
        content = ChannelOutput.model_validate(response.json())
        assert content == channel

    def test_get_public_channel_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=True)
        channel = create_channel_api(client, user_1, data)
        response = get_channel_api(client, channel.id, user_2)
        assert response == channel

    def test_get_channel_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}",
            detail="Channel not found",
            headers=user.headers,
        )

    def test_get_private_channel_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=False)
        channel = create_channel_api(client, user_1, data)
        assert_not_enough_permission(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
            user=user_2,
        )

    def test_get_private_channel_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=False)
        channel = create_channel_api(client, user, data)
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
        )


class TestListChannels:
    def test_list_channels(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        create_channel_api(client, user)
        create_channel_api(client, user)

        response = client.get(
            f"{settings.API_V1_STR}/channels/",
            headers=user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = MultipleChannelOutputs.model_validate(response.json())
        assert content.count >= 2

    def test_list_channels_as_superuser(
        self,
        client: TestClient,
        db: Session,
        super_user: CreatedUser,
    ) -> None:
        user = create_random_user_alt(client, db)
        create_channel_api(client, user)

        response = client.get(
            f"{settings.API_V1_STR}/channels/",
            headers=super_user.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        content = MultipleChannelOutputs.model_validate(response.json())
        assert content.count >= 1

    def test_list_channels_not_authenticated(self, client: TestClient) -> None:
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/",
        )

    def test_list_channels_pagination(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        total_channels = 150
        channels = [create_channel_api(client, user) for _ in range(total_channels)]
        get_channels_api(client, user, expected_output=channels)


class TestUpdateChannel:
    def test_update_channel(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        data = dump_random_model(ChannelInput)

        assert_success(
            client=client,
            method="put",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
            output_model=ChannelOutput,
            headers=user.headers,
            parameters=data,
        )

    def test_update_channel_duplicate_name(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel_1 = create_channel_api(client, user)
        channel_2 = create_channel_api(client, user)

        assert_conflict(
            client=client,
            method="put",
            url=f"{settings.API_V1_STR}/channels/{channel_2.id}",
            detail="Channel with this name already exists",
            headers=user.headers,
            parameters=dump_random_model(ChannelInput, name=channel_1.name),
        )

    def test_update_channel_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="put",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}",
            detail="Channel not found",
            headers=user.headers,
            parameters=dump_random_model(ChannelInput),
        )

    def test_update_channel_wrong_user(self, client: TestClient, db: Session) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        channel = create_channel_api(client, user_1)
        assert_not_enough_permission(
            client=client,
            method="put",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
            user=user_2,
            parameters=dump_random_model(ChannelInput),
        )

    def test_update_channel_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        assert_not_authenticated(
            client=client,
            method="put",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
            parameters=dump_random_model(ChannelInput),
        )


class TestDeleteChannel:
    def test_delete_channel(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        assert_delete(
            client=client,
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
            message="Channel deleted successfully",
            headers=user.headers,
        )

    def test_delete_channel_not_found(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}",
            detail="Channel not found",
            headers=user.headers,
        )

    def test_delete_channel_wrong_user(self, client: TestClient, db: Session) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        channel = create_channel_api(client, user_1)
        assert_not_enough_permission(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
            user=user_2,
        )

    def test_delete_channel_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{channel.id}",
        )


class TestChannelEpisodes:
    def test_get_channel_with_episodes(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
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
        get_channel_episodes_api(client, user, channel, episodes)

    def test_get_channel_with_no_episodes(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        get_channel_episodes_api(client, user, channel, [])

    def test_get_channel_episodes_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=False)
        channel = create_channel_api(client, user, data)
        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/episodes",
        )

    def test_get_channel_episodes_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        data = dump_random_model(ChannelInput, public=False)
        channel = create_channel_api(client, user_1, data)
        assert_not_enough_permission(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/episodes",
            user=user_2,
        )


class TestQueueAddURL:
    @pytest.mark.parametrize(
        ("initial_url_count", "new_url_count"),
        [(i, j) for i in range(3) for j in range(3)],
    )
    def test_append_urls_to_queue(
        self,
        client: TestClient,
        db: Session,
        initial_url_count: int,
        new_url_count: int,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)

        response = add_urls_to_channel_queue_api(
            client,
            channel,
            user,
            [random_lower_string() for _ in range(initial_url_count)],
        )
        response.data = response.data[::-1]

        response_2 = add_urls_to_channel_queue_api(
            client,
            channel,
            user,
            [random_lower_string() for _ in range(new_url_count)],
        )
        response_2.data = response_2.data[::-1]

        expected_response = MultipleChannelQueueOutputs(
            data=response_2.data + response.data,
            count=response_2.count + response.count,
        )

        get_channel_queue_api(client, user, channel, expected_response)

    def test_append_existing_url(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        first_url = random_lower_string()
        add_urls_to_channel_queue_api(client, channel, user, [first_url])

        response = add_urls_to_channel_queue_api(client, channel, user, [first_url])
        get_channel_queue_api(client, user, channel, response)

    def test_append_duplicate_urls(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        random_url = random_lower_string()

        response = add_urls_to_channel_queue_api(
            client,
            channel,
            user,
            [random_url, random_url],
        )
        response.data = response.data[::-1]
        get_channel_queue_api(client, user, channel, response)

    def test_append_urls_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        response = add_urls_to_channel_queue_api(client, channel, user)

        assert_not_authenticated(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
            parameters=[random_lower_string()],
        )

        # Make sure the channel queue is unchanged
        get_channel_queue_api(client, user, channel, response)

    def test_append_urls_wrong_user(self, client: TestClient, db: Session) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        channel = create_channel_api(client, user_1)
        response = add_urls_to_channel_queue_api(client, channel, user_1)

        assert_not_enough_permission(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
            user=user_2,
            parameters=[random_lower_string()],
        )

        # Make sure the channel queue is unchanged
        get_channel_queue_api(client, user_1, channel, response)


class TestQueueDeleteURL:
    def test_delete_url_in_queue(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        response = add_urls_to_channel_queue_api(
            client,
            channel,
            user,
            [random_lower_string() for _ in range(4)],
        )

        response_clone = response.model_copy()
        response.data = response.data[::-1]

        for queue_entry in response_clone.data:
            delete_channel_queue_url_api(client, user, channel, queue_entry)
            response.data.pop()
            response.count -= 1

        get_channel_queue_api(client, user, channel, response)

    def test_delete_invalid_url(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        response = add_urls_to_channel_queue_api(client, channel, user)

        assert_not_found(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{uuid.uuid4()}",
            detail="URL not found",
            headers=user.headers,
        )

        # Make sure the channel queue is unchanged
        get_channel_queue_api(client, user, channel, response)

    def test_delete_from_queue_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel = create_channel_api(client, user)
        response = add_urls_to_channel_queue_api(client, channel, user)

        assert_not_authenticated(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{response.data[0].id}",
        )

        # Make sure the channel queue is unchanged
        get_channel_queue_api(client, user, channel, response)

    def test_delete_from_queue_wrong_user(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)
        channel = create_channel_api(client, user_1)
        response = add_urls_to_channel_queue_api(client, channel, user_1)

        assert_not_enough_permission(
            client=client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{response.data[0].id}",
            user=user_2,
        )

        # Make sure the channel queue is unchanged
        get_channel_queue_api(client, user_1, channel, response)


class TestWhitelist:
    def test_get_channel_show_whitelist(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel_show = initialize_whitelist_data(client, db, user)
        response = get_channel_show_whitelist_api(client, channel_show, user)

        whitelist_input = whitelist_output_to_input(response)

        season_alternator = False
        for season in whitelist_input.seasons:
            season_alternator = not season_alternator
            assert season.enabled == season_alternator

            episode_alternator = False
            for episode in season.episodes:
                episode_alternator = not episode_alternator
                assert episode.enabled == episode_alternator

    def test_set_channel_show_whitelist(self, client: TestClient, db: Session) -> None:
        user = create_random_user_alt(client, db)
        channel_show = initialize_whitelist_data(client, db, user)
        response = get_channel_show_whitelist_api(client, channel_show, user)

        whitelist_input = whitelist_output_to_input(response)
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
            user,
            whitelist_input,
        )
        assert whitelist_input == whitelist_output_to_input(response)

        get_channel_show_whitelist_api(client, channel_show, user, whitelist_input)

    def test_get_channel_show_whitelist_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        channel_show = initialize_whitelist_data(client, db)

        assert_not_authenticated(
            client=client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel_show.channel_id}/whitelist/{channel_show.show_id}",
        )

    def test_set_channel_show_whitelist_not_authenticated(
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user = create_random_user_alt(client, db)
        channel_show = initialize_whitelist_data(client, db, user)

        response = get_channel_show_whitelist_api(client, channel_show, user)

        whitelist_input = whitelist_output_to_input(response)
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
        self,
        client: TestClient,
        db: Session,
    ) -> None:
        user_1 = create_random_user_alt(client, db)
        user_2 = create_random_user_alt(client, db)

        channel_show = initialize_whitelist_data(client, db, user_1)
        channel_show_2 = initialize_whitelist_data(client, db, user_2)

        channel_2 = create_channel_api(client, user_2)
        db.add(channel_show_2)
        db.commit()

        response = get_channel_show_whitelist_api(client, channel_show_2, user_2)

        whitelist_input = whitelist_output_to_input(response)

        assert_not_found(
            client=client,
            method="post",
            url=f"{settings.API_V1_STR}/channels/{channel_2.id}/whitelist/{channel_show.id}",
            detail="Show was not found on channel",
            headers=user_2.headers,
            parameters=json.loads(whitelist_input.model_dump_json()),
        )
