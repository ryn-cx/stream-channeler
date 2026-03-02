# TODO: Validate
import uuid
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient

from app.channels.models import Channel
from app.channels.schemas import (
    ChannelEpisodesOutput,
    ChannelInput,
    ChannelOutput,
    ChannelQueueOutput,
    MultipleChannelOutputs,
    MultipleChannelQueueOutputs,
)
from app.config import settings
from app.constants import MAX_ENTRIES_PER_PAGE
from app.media.models import Episode
from app.models import Message
from tests.utils.user import CreatedUser, create_random_user_alt
from tests.utils.utils import dump_random_model, random_lower_string


def get_random_channel(public: bool = False) -> Channel:
    return Channel(name=random_lower_string(), public=public)


def get_channels_api(
    client: TestClient,
    user: CreatedUser | None = None,
    params: str = "",
    expected_output: list[ChannelOutput] | None = None,
) -> MultipleChannelOutputs:
    user = user or create_random_user_alt(client)
    headers = user.headers

    response = client.get(
        f"{settings.API_V1_STR}/channels/{params}",
        headers=headers or None,
    )

    assert response.status_code == status.HTTP_200_OK
    output = MultipleChannelOutputs.model_validate(response.json())

    if expected_output:
        # Sort by name to match the API output
        expected_output.sort(key=lambda x: x.name)
        expected_count = len(expected_output)

        # Paginate and concatenate the results.
        response_channels = output.data
        if expected_count > MAX_ENTRIES_PER_PAGE:
            for i in range(MAX_ENTRIES_PER_PAGE, expected_count, MAX_ENTRIES_PER_PAGE):
                params = f"?skip={i}"

                # Get the channels for the current page
                response = get_channels_api(client, user, params)
                response_channels.extend(response.data)
                assert response.count == expected_count

            assert response_channels == expected_output

    return output


def add_urls_to_channel_queue_api(
    client: TestClient,
    channel: ChannelOutput,
    user: CreatedUser | None = None,
    urls: list[str] | None = None,
    expected_output: MultipleChannelQueueOutputs | None = None,
) -> MultipleChannelQueueOutputs:
    urls = urls or [random_lower_string()]
    user = user or create_random_user_alt(client)
    headers = user.headers

    response = client.post(
        f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
        headers=headers,
        json=urls,
    )

    assert response.status_code == status.HTTP_200_OK

    output = MultipleChannelQueueOutputs.model_validate(response.json())

    if expected_output:
        assert output == expected_output

    return output


def create_channel_api(
    client: TestClient,
    user: CreatedUser | None = None,
    data: dict[str, Any] | None = None,
) -> ChannelOutput:
    user = user or create_random_user_alt(client)
    data = data or dump_random_model(ChannelInput, name=random_lower_string())

    response = client.post(
        f"{settings.API_V1_STR}/channels/",
        headers=user.headers,
        json=data,
    )
    assert response.status_code == status.HTTP_200_OK
    return ChannelOutput.model_validate(response.json())


def get_channel_api(
    client: TestClient,
    channel_id: uuid.UUID,
    user: CreatedUser | None = None,
) -> ChannelOutput:
    user = user or create_random_user_alt(client)

    response = client.get(
        f"{settings.API_V1_STR}/channels/{channel_id}",
        headers=user.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    return ChannelOutput.model_validate(response.json())


def update_channel_api(
    client: TestClient,
    channel_id: uuid.UUID,
    user: CreatedUser | None = None,
    update_data: dict[str, Any] | None = None,
    expected_output: ChannelOutput | None = None,
) -> ChannelOutput:
    user = user or create_random_user_alt(client)

    response = client.put(
        f"{settings.API_V1_STR}/channels/{channel_id}",
        headers=user.headers,
        json=update_data,
    )

    assert response.status_code == status.HTTP_200_OK

    output = ChannelOutput.model_validate(response.json())

    if expected_output:
        assert expected_output == output

    return output


def delete_channel_api(
    client: TestClient,
    channel_id: uuid.UUID,
    user: CreatedUser | None = None,
) -> Message:
    user = user or create_random_user_alt(client)
    headers = user.headers
    response = client.delete(
        f"{settings.API_V1_STR}/channels/{channel_id}",
        headers=headers,
    )

    assert response.status_code == status.HTTP_200_OK
    output = Message.model_validate(response.json())
    assert output.message == "Channel deleted successfully"
    return output


def get_channel_queue_api(
    client: TestClient,
    user: CreatedUser,
    channel: ChannelOutput,
    expected_output: MultipleChannelQueueOutputs | None = None,
) -> MultipleChannelQueueOutputs:
    response = client.get(
        f"{settings.API_V1_STR}/channels/{channel.id}/import-queue",
        headers=user.headers,
    )

    assert response.status_code == status.HTTP_200_OK
    output = MultipleChannelQueueOutputs.model_validate(response.json())

    if expected_output:
        assert output == expected_output

    return output


def delete_channel_queue_url_api(
    client: TestClient,
    user: CreatedUser,
    channel: ChannelOutput,
    queue_entry: ChannelQueueOutput,
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/channels/{channel.id}/import-queue/{queue_entry.id}",
        headers=user.headers,
    )

    assert response.status_code == status.HTTP_200_OK
    expected_message = f"{queue_entry.url} removed from import queue successfully"
    assert response.json()["message"] == expected_message


def get_channel_episodes_api(
    client: TestClient,
    random_user: CreatedUser,
    channel: ChannelOutput,
    expected_response: list[Episode] | None = None,
) -> ChannelEpisodesOutput:
    response = client.get(
        f"{settings.API_V1_STR}/channels/{channel.id}/episodes",
        headers=random_user.headers,
    )
    assert response.status_code == status.HTTP_200_OK
    output = ChannelEpisodesOutput.model_validate(response.json())

    if expected_response:
        # TODO: Actually implement the comparison
        assert True

    return output
