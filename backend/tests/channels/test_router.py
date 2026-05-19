# TODO: Validate


import uuid
from dataclasses import dataclass
from typing import Any, Literal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channels.models import Channel, ChannelShow, URLStatus
from app.channels.schemas import (
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelOptions,
    ChannelOutput,
    ChannelQueueOutput,
    ChannelShowsOutput,
    ChannelUpdate,
    EpisodeWithDetails,
    SortOptionOutput,
    WhitelistEntryInput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.channels.service import update_whitelist
from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.models import Visibility
from app.plugins.schemas import PluginOutput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.models import User
from tests.channels.utils import (
    create_random_channel,
    create_random_channel_queue,
    create_random_channel_show,
)
from tests.episodes.utils import create_random_episode
from tests.plugins.utils import create_random_plugin
from tests.shows.utils import create_random_show
from tests.users.utils import authentication_token_from_email, create_random_user
from tests.utils.base import BaseTests
from tests.utils.base_create import UserOwnedCreateMixin
from tests.utils.base_delete import BaseDeleteTests
from tests.utils.base_get import UserOwnedGetMixin
from tests.utils.base_update import BaseUpdateTests
from tests.utils.route_assertions import (
    Method,
    assert_delete,
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
    assert_success,
    assert_success_list,
    make_request,
)
from tests.utils.utils import dump_random_model, random_lower_string

SKIP_REASON = "Channels use /channels, not /users/{id}/channels"
SORT_OPTIONS_URL = f"{settings.API_V1_STR}/channels/sort-options"


class ChannelTestMixin(BaseTests[Channel]):
    database_model = Channel
    create_schema = ChannelCreate
    output_schema = ChannelOutput
    update_schema = ChannelUpdate
    create_record_function = staticmethod(create_random_channel)

    # Channels do not rely on plugins for visibility and instead have their own
    # visibility column.
    def set_visibility(self, record: Channel, *, record_is_public: bool) -> None:
        record.visibility = (
            Visibility.public if record_is_public else Visibility.private
        )


class TestCreateChannel(ChannelTestMixin, UserOwnedCreateMixin[Channel]):
    pass


class TestGetChannel(ChannelTestMixin, UserOwnedGetMixin[Channel]):
    pass


class TestUpdateChannel(ChannelTestMixin, BaseUpdateTests[Channel]):
    pass


class TestDeleteChannel(ChannelTestMixin, BaseDeleteTests[Channel]):
    pass


class TestSortOptions:
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    def test_sort_options(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
    ) -> None:
        headers = {}
        if user_is_authenticated:
            user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=user.email,
                session=session_scoped_session,
            )
        result = assert_success_list(
            client=session_scoped_client,
            method="get",
            url=SORT_OPTIONS_URL,
            output_schema=SortOptionOutput,
            headers=headers,
        )
        assert len(result) > 0


class BaseChannelSubEndpointTests(ChannelTestMixin):
    sub_http_method: Method
    sub_parameters: dict[str, Any] | list[Any] | None = None

    def sub_url(self, channel_id: uuid.UUID) -> str:
        raise NotImplementedError

    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        return (user_is_authenticated and user_is_owner) or record_is_public

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_get_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
        )

        url = self.sub_url(initial_test_data.record.id)
        if self.can_access_sub_endpoint(
            user_is_authenticated=user_is_authenticated,
            user_is_owner=user_is_owner,
            record_is_public=record_is_public,
        ):
            response = make_request(
                session_scoped_client,
                self.sub_http_method,
                url,
                headers=initial_test_data.headers,
                parameters=self.sub_parameters,
            )
            assert response.status_code not in {
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            }
        else:
            self.assert_cannot_access(
                session_scoped_session,
                session_scoped_client,
                user_is_authenticated=user_is_authenticated,
                method=self.sub_http_method,
                url=url,
                model_name=self.model_name,
                headers=initial_test_data.headers,
            )

    def test_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        assert_not_found(
            client=session_scoped_client,
            method=self.sub_http_method,
            url=self.sub_url(uuid.uuid4()),
            detail=f"{self.model_name} not found",
            headers=initial_test_data.headers,
            parameters=self.sub_parameters,
        )


class TestUpdateDefaultOrder:
    @staticmethod
    def url(channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel_id}/default-order"

    def assert_update(
        self,
        session_scoped_client: TestClient,
        channel_id: uuid.UUID,
        headers: dict[str, str],
        mode: Literal["minimal", "full"],
    ) -> ChannelOutput:
        response = session_scoped_client.patch(
            self.url(channel_id),
            json=dump_random_model(ChannelOptions, mode),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        return ChannelOutput.model_validate(response.json())

    @pytest.mark.parametrize("initial_mode", ["minimal", "full"])
    @pytest.mark.parametrize("update_mode", ["minimal", "full"])
    def test_update_default_order(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        initial_mode: Literal["minimal", "full"],
        update_mode: Literal["minimal", "full"],
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(session_scoped_session, user=user.id)

        self.assert_update(
            session_scoped_client,
            channel.id,
            user_headers,
            initial_mode,
        )
        self.assert_update(session_scoped_client, channel.id, user_headers, update_mode)

    @pytest.mark.parametrize("user_type", ["normal_user", "anon"])
    def test_update_default_order_errors(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        user_type: str,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        channel = create_random_channel(session_scoped_session, user=owner.id)

        if user_type == "normal_user":
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="patch",
                url=self.url(channel.id),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
        else:
            assert_not_authenticated(
                client=session_scoped_client,
                method="patch",
                url=self.url(channel.id),
            )

    def test_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        assert_not_found(
            client=session_scoped_client,
            method="patch",
            url=self.url(uuid.uuid4()),
            detail="Channel not found",
            headers=user_headers,
        )


class TestChannelEpisodes(BaseChannelSubEndpointTests):
    sub_http_method = "get"
    sub_parameters = None

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel_id}/episodes"

    @pytest.mark.skip(reason="Covered by test_with_episodes and test_no_episodes")
    def test_get_permissions(self) -> None:  # type: ignore[override]
        pass

    def generic_record_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/channels/{record_id}/episodes"

    @staticmethod
    def create_channel_with_episodes(
        session_scoped_session: Session,
        user_id: uuid.UUID,
        *,
        is_public: bool,
    ) -> tuple[Channel, ChannelEpisodesOutput]:
        channel = create_random_channel(
            session_scoped_session,
            user=user_id,
            is_public=is_public,
        )

        expected = ChannelEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
            channels={},
        )
        expected.channels[channel.id] = ChannelOutput.model_validate(channel)

        for _ in range(2):
            plugin = create_random_plugin(
                session_scoped_session,
                user_id,
                visibility=Visibility.public,
            )
            channel_show = create_random_channel_show(
                session_scoped_session,
                channel,
                plugin,
                is_whitelist=False,
            )
            show = channel_show.show
            create_random_episode(session_scoped_session, show)
            source = show.source
            plugin = source.plugin
            season = show.seasons[0]
            episode = season.episodes[0]

            expected.episodes.append(
                EpisodeWithDetails(**episode.model_dump(), channel_id=channel.id),
            )
            expected.seasons[season.id] = SeasonOutput.model_validate(season)
            expected.shows[show.id] = ShowPublic.model_validate(show)
            expected.sources[source.id] = SourcePublic.model_validate(source)
            expected.plugins[plugin.id] = PluginOutput.model_validate(plugin)

        return channel, expected

    @staticmethod
    def assert_episodes(
        response_data: ChannelEpisodesOutput,
        expected: ChannelEpisodesOutput,
    ) -> None:
        response_data.episodes.sort(key=lambda e: e.id)
        expected.episodes.sort(key=lambda e: e.id)
        assert response_data.episodes == expected.episodes
        assert response_data.seasons == expected.seasons
        assert response_data.shows == expected.shows
        assert response_data.sources == expected.sources
        assert response_data.plugins == expected.plugins
        assert response_data.channels == expected.channels
        assert response_data == expected

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_with_episodes(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        record_is_public: bool,
        user_is_authenticated: bool,
        user_is_owner: bool,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel, expected = self.create_channel_with_episodes(
            session_scoped_session,
            owner.id,
            is_public=record_is_public,
        )

        if not user_is_authenticated and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
            )
            return
        if user_is_authenticated and not user_is_owner and not record_is_public:
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
            return

        if user_is_owner:
            headers = owner_headers
        elif user_is_authenticated:
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}
        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        response_data = ChannelEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        self.assert_episodes(response_data, expected)

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_no_episodes(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        record_is_public: bool,
        user_is_authenticated: bool,
        user_is_owner: bool,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=owner.id,
            is_public=record_is_public,
        )
        expected = ChannelEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
            channels={},
        )

        if not user_is_authenticated and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
            )
            return
        if user_is_authenticated and not user_is_owner and not record_is_public:
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(channel.id),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
            return

        if user_is_owner:
            headers = owner_headers
        elif user_is_authenticated:
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}
        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        response_data = ChannelEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        assert response_data == expected

    @pytest.mark.parametrize(
        "user_type",
        ["owner", "plugin_owner", "normal_user", "anon"],
    )
    def test_private_plugin_visibility(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        user_type: str,
    ) -> None:
        """Episodes from private plugins should only be visible to the plugin owner."""
        channel_owner = create_random_user(session_scoped_session)
        channel_owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=channel_owner.email,
            session=session_scoped_session,
        )
        plugin_owner = create_random_user(session_scoped_session)
        plugin_owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=plugin_owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=channel_owner.id,
            is_public=True,
        )

        # Add a show from a private plugin owned by plugin_owner
        private_plugin = create_random_plugin(
            session_scoped_session,
            plugin_owner.id,
            visibility=Visibility.private,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            private_plugin,
            is_whitelist=False,
        )
        show = channel_show.show
        create_random_episode(session_scoped_session, show)

        if user_type == "owner":
            headers = channel_owner_headers
        elif user_type == "plugin_owner":
            headers = plugin_owner_headers
        elif user_type == "normal_user":
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}

        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = ChannelEpisodesOutput.model_validate(response.json())

        if user_type == "plugin_owner":
            assert len(data.episodes) == 1
            assert len(data.seasons) == 1
            assert len(data.shows) == 1
            assert len(data.sources) == 1
            assert len(data.plugins) == 1
            assert len(data.channels) == 1
        else:
            assert not data.episodes
            assert not data.seasons
            assert not data.shows
            assert not data.sources
            assert not data.plugins
            assert not data.channels

    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_public_plugin_visibility(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
    ) -> None:
        """Episodes from public plugins should be visible to all users."""
        channel_owner = create_random_user(session_scoped_session)
        channel_owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=channel_owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=channel_owner.id,
            is_public=True,
        )

        public_plugin = create_random_plugin(
            session_scoped_session,
            channel_owner.id,
            visibility=Visibility.public,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            channel,
            public_plugin,
            is_whitelist=False,
        )
        show = channel_show.show
        create_random_episode(session_scoped_session, show)

        if user_is_owner:
            headers = channel_owner_headers
        elif user_is_authenticated:
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}

        response = session_scoped_client.get(
            self.generic_record_url(channel.id),
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = ChannelEpisodesOutput.model_validate(response.json())
        assert len(data.episodes) == 1


class TestListChannelShows:
    @staticmethod
    def url(channel: Channel | ChannelOutput) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/shows"

    @staticmethod
    def build_expected(channel: Channel) -> ChannelShowsOutput:
        expected = ChannelShowsOutput()
        for channel_show in channel.shows:
            show = channel_show.show
            source = show.source
            expected.shows.append(ShowPublic.model_validate(show))
            if source.id not in expected.sources:
                expected.sources[source.id] = SourcePublic.model_validate(source)
        return expected

    @pytest.mark.parametrize("show_count", [0, 1, 2])
    def test_list_shows_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        show_count: int,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(session_scoped_session, user=owner.id)
        for _ in range(show_count):
            create_random_channel_show(session_scoped_session, channel, owner)

        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=self.url(channel),
            output_schema=ChannelShowsOutput,
            headers=owner_headers,
        )
        expected = self.build_expected(channel)
        assert result.shows == expected.shows
        assert result.sources == expected.sources

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_type", ["owner", "normal_user", "anonymous"])
    def test_list_shows_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        record_is_public: bool,
        user_type: str,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=owner.id,
            is_public=record_is_public,
        )
        show = create_random_show(
            session_scoped_session,
            owner.id,
            name=random_lower_string(),
        )
        create_random_channel_show(session_scoped_session, channel, show)

        if user_type == "normal_user" and not record_is_public:
            other_user = create_random_user(session_scoped_session)
            other_headers = authentication_token_from_email(
                client=session_scoped_client,
                email=other_user.email,
                session=session_scoped_session,
            )
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=self.url(channel),
                detail="Not authorized to access this Channel",
                headers=other_headers,
            )
            return
        if user_type == "anonymous" and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.url(channel),
            )
            return

        if user_type == "owner":
            headers = owner_headers
        elif user_type == "normal_user":
            normal_user = create_random_user(session_scoped_session)
            headers = authentication_token_from_email(
                client=session_scoped_client,
                email=normal_user.email,
                session=session_scoped_session,
            )
        else:
            headers = {}

        assert_success(
            client=session_scoped_client,
            method="get",
            url=self.url(channel),
            output_schema=ChannelShowsOutput,
            headers=headers,
        )

    def test_list_shows_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        assert_not_found(
            client=session_scoped_client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/shows",
            detail="Channel not found",
            headers=user_headers,
        )


class TestDeleteChannelShow:
    @staticmethod
    def url(channel: Channel | ChannelOutput, show_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/channels/{channel.id}/remove-show/{show_id}"

    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_remove_show_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        record_is_public: bool,
        user_is_authenticated: bool,
        user_is_owner: bool,
    ) -> None:
        owner = create_random_user(session_scoped_session)
        owner_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=owner.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(
            session_scoped_session,
            user=owner.id,
            is_public=record_is_public,
        )
        show = create_random_show(
            session_scoped_session,
            owner.id,
            name=random_lower_string(),
        )
        create_random_channel_show(session_scoped_session, channel, show)

        if not user_is_authenticated:
            assert_not_authenticated(
                client=session_scoped_client,
                method="delete",
                url=self.url(channel, show.id),
            )
            return

        if user_is_owner:
            assert_delete(
                client=session_scoped_client,
                url=self.url(channel, show.id),
                message=f"{show.name} removed from channel successfully",
                headers=owner_headers,
            )
            return

        other_user = create_random_user(session_scoped_session)
        other_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=other_user.email,
            session=session_scoped_session,
        )
        assert_forbidden(
            client=session_scoped_client,
            method="delete",
            url=self.url(channel, show.id),
            detail="Not authorized to access this Channel",
            headers=other_headers,
        )

    def test_remove_show_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(session_scoped_session, user=user.id)

        assert_not_found(
            client=session_scoped_client,
            method="delete",
            url=self.url(channel, uuid.uuid4()),
            detail="Show not found",
            headers=user_headers,
        )

    def test_remove_show_not_in_channel(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        channel = create_random_channel(session_scoped_session, user=user.id)
        # Create the show on a different channel.
        other_channel = create_random_channel(session_scoped_session, user=user.id)
        other_channel_show = create_random_channel_show(
            session_scoped_session,
            other_channel,
        )

        assert_not_found(
            client=session_scoped_client,
            method="delete",
            url=self.url(channel, other_channel_show.show_id),
            detail="Show was not found on channel",
            headers=user_headers,
        )

    def test_remove_show_channel_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        user_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        assert_not_found(
            client=session_scoped_client,
            method="delete",
            url=f"{settings.API_V1_STR}/channels/{uuid.uuid4()}/remove-show/{uuid.uuid4()}",
            detail="Channel not found",
            headers=user_headers,
        )


class BaseChannelQueueTests(BaseChannelSubEndpointTests):
    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def queue_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/import-queue"

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return self.queue_url(channel_id)

    def queue_parameters(self) -> list[str] | None:
        return None

    def assert_queue_contents(
        self,
        session_scoped_client: TestClient,
        channel: Channel,
        headers: dict[str, str],
        expected_urls: list[str],
    ) -> None:
        result = assert_success_list(
            client=session_scoped_client,
            method="get",
            url=self.queue_url(channel.id),
            output_schema=ChannelQueueOutput,
            headers=headers,
        )
        assert [record.url for record in result] == expected_urls

    def test_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        assert_not_found(
            client=session_scoped_client,
            method=self.sub_http_method,
            url=self.queue_url(uuid.uuid4()),
            detail=f"{self.model_name} not found",
            headers=initial_test_data.headers,
            parameters=self.queue_parameters(),
        )


class TestQueueGet(BaseChannelQueueTests):
    sub_http_method = "get"

    def test_get_queue(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        queue_entry_1 = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )
        queue_entry_2 = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )

        self.assert_queue_contents(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            expected_urls=[queue_entry_2.url, queue_entry_1.url],
        )

    def test_get_queue_empty(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        self.assert_queue_contents(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            expected_urls=[],
        )


class TestQueueAddURL(BaseChannelQueueTests):
    sub_http_method = "post"
    sub_parameters = ["placeholder"]

    def queue_parameters(self) -> list[str]:
        return [random_lower_string()]

    def assert_add_urls(
        self,
        session_scoped_client: TestClient,
        channel: Channel,
        headers: dict[str, str],
        urls: list[str],
        expected_urls: list[str],
    ) -> None:
        assert_success_list(
            client=session_scoped_client,
            method="post",
            url=self.queue_url(channel.id),
            output_schema=ChannelQueueOutput,
            headers=headers,
            parameters=urls,
        )
        self.assert_queue_contents(
            session_scoped_client,
            channel,
            headers,
            expected_urls,
        )

    @pytest.mark.parametrize("initial_url_count", [0, 1, 2])
    @pytest.mark.parametrize("new_url_count", [0, 1, 2])
    def test_append_urls(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        initial_url_count: int,
        new_url_count: int,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        initial_urls = [
            create_random_channel_queue(
                session_scoped_session,
                initial_test_data.record,
            ).url
            for _ in range(initial_url_count)
        ]

        new_urls = [random_lower_string() for _ in range(new_url_count)]
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=new_urls,
            expected_urls=new_urls[::-1] + initial_urls[::-1],
        )

    def test_append_existing_url(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        existing = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=[existing.url],
            expected_urls=[existing.url],
        )

    def test_append_duplicate_urls(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        random_url = random_lower_string()
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=[random_url, random_url],
            expected_urls=[random_url],
        )

    def test_append_duplicate_existing_url(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        existing = create_random_channel_queue(
            session_scoped_session,
            initial_test_data.record,
        )
        self.assert_add_urls(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            urls=[existing.url],
            expected_urls=[existing.url],
        )


class TestQueueDeleteURL(BaseChannelQueueTests):
    sub_http_method = "delete"

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{self.queue_url(channel_id)}/{uuid.uuid4()}"

    def queue_entry_url(self, channel: Channel, entry_id: uuid.UUID) -> str:
        return f"{self.queue_url(channel.id)}/{entry_id}"

    def test_delete_url(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        queue_entries = [
            create_random_channel_queue(
                session_scoped_session,
                initial_test_data.record,
            )
            for _ in range(3)
        ]

        for queue_entry in queue_entries:
            assert_delete(
                client=session_scoped_client,
                url=self.queue_entry_url(initial_test_data.record, queue_entry.id),
                message=f"{queue_entry.url} removed from import queue successfully",
                headers=initial_test_data.headers,
            )

        self.assert_queue_contents(
            session_scoped_client,
            initial_test_data.record,
            initial_test_data.headers,
            expected_urls=[],
        )

    def test_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )

        assert_not_found(
            client=session_scoped_client,
            method="delete",
            url=self.queue_entry_url(initial_test_data.record, uuid.uuid4()),
            detail="URL not found",
            headers=initial_test_data.headers,
        )


class TestClearCompletedQueue(BaseChannelSubEndpointTests):
    sub_http_method = "delete"

    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/clear-completed-import-queue"

    @pytest.mark.parametrize(
        ("initial_statuses", "expected_remaining"),
        [
            (
                [URLStatus.IMPORTED, URLStatus.IMPORTED, URLStatus.PENDING],
                [URLStatus.PENDING],
            ),
            (
                [URLStatus.PENDING, URLStatus.FAILED],
                [URLStatus.PENDING, URLStatus.FAILED],
            ),
            ([], []),
        ],
        ids=["with_completed", "no_completed", "empty"],
    )
    def test_clear_completed(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        initial_statuses: list[URLStatus],
        expected_remaining: list[URLStatus],
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        records = [
            create_random_channel_queue(
                session_scoped_session,
                initial_test_data.record,
                status=s,
            )
            for s in initial_statuses
        ]

        response = session_scoped_client.delete(
            self.sub_url(initial_test_data.record.id),
            headers=initial_test_data.headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Import queue cleared successfully"

        result = assert_success_list(
            client=session_scoped_client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{initial_test_data.record.id}/import-queue",
            output_schema=ChannelQueueOutput,
            headers=initial_test_data.headers,
        )
        remaining_urls = {record.url for record in result}
        expected_urls = {
            r.url
            for r, s in zip(records, initial_statuses, strict=True)
            if s in expected_remaining
        }
        assert remaining_urls == expected_urls


class TestGetWhitelist(BaseChannelSubEndpointTests):
    sub_http_method = "get"

    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/whitelist/{uuid.uuid4()}"

    def assert_whitelist_success(
        self,
        session_scoped_client: TestClient,
        channel: Channel,
        channel_show: ChannelShow,
        episodes: list[Episode],
        headers: dict[str, str],
        *,
        expected_season_ids: list[uuid.UUID] | None = None,
        expected_episode_ids: list[uuid.UUID] | None = None,
    ) -> None:
        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=f"{settings.API_V1_STR}/channels/{channel.id}/whitelist/{channel_show.show_id}",
            output_schema=WhitelistShowOutput,
            headers=headers,
        )
        assert result.is_whitelist == channel_show.is_whitelist
        actual_season_ids = [s.id for s in result.seasons if s.filtered]
        actual_episode_ids = [e.id for e in result.episodes if e.filtered]
        assert actual_season_ids == (expected_season_ids or [])
        assert actual_episode_ids == (expected_episode_ids or [])
        assert [EpisodeOutput.model_validate(e) for e in result.episodes] == [
            EpisodeOutput.model_validate(episode) for episode in episodes
        ]

    @pytest.mark.parametrize("plugin_is_public", [True, False])
    @pytest.mark.parametrize("user_owns_plugin", [True, False])
    def test_get_shows_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_owns_plugin: bool,
        plugin_is_public: bool,
    ) -> None:
        """Test show listing with plugin visibility and plugin ownership.

        The channel is public and the user is the channel owner. Shows from
        private plugins should only be visible if the user also owns the plugin.
        """
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=True,
        )
        plugin_owner = (
            initial_test_data.user
            if user_owns_plugin
            else create_random_user(session_scoped_session)
        )
        plugin = create_random_plugin(
            session_scoped_session,
            plugin_owner,
            visibility=Visibility.public if plugin_is_public else Visibility.private,
        )

        show = create_random_show(session_scoped_session, plugin)
        create_random_episode(session_scoped_session, show)
        create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            show,
        )

        url = f"{settings.API_V1_STR}/channels/{initial_test_data.record.id}/shows"
        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=url,
            output_schema=ChannelShowsOutput,
            headers=initial_test_data.headers,
        )
        if plugin_is_public or user_owns_plugin:
            assert len(result.shows) == 1
        else:
            assert len(result.shows) == 0

    @pytest.mark.parametrize("plugin_is_public", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_get_whitelist_permissions(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_owner: bool,
        plugin_is_public: bool,
    ) -> None:
        """Test whitelist endpoint with plugin visibility and channel ownership.

        The whitelist endpoint requires channel ownership AND that the show is
        readable. Non-owners get a channel permission error. Owners with an
        unreadable show (private plugin owned by someone else) get a show
        permission error.
        """
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=True,
            record_is_public=True,
        )
        other_user = create_random_user(session_scoped_session)
        plugin = create_random_plugin(
            session_scoped_session,
            other_user,
            visibility=Visibility.public if plugin_is_public else Visibility.private,
        )
        show = create_random_show(session_scoped_session, plugin)
        channel_show = create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            show,
        )
        episode = create_random_episode(session_scoped_session, channel_show.show)

        url = f"{settings.API_V1_STR}/channels/{initial_test_data.record.id}/whitelist/{channel_show.show_id}"
        if user_is_owner and plugin_is_public:
            self.assert_whitelist_success(
                session_scoped_client,
                initial_test_data.record,
                channel_show,
                [episode],
                initial_test_data.headers,
            )
        elif not user_is_owner:
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=url,
                detail="Not authorized to access this Channel",
                headers=initial_test_data.headers,
            )
        else:
            assert_forbidden(
                client=session_scoped_client,
                method="get",
                url=url,
                detail="Not authorized to access this Show",
                headers=initial_test_data.headers,
            )

    @pytest.mark.parametrize("episode_count", [0, 1, 2])
    def test_read_whitelist(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        episode_count: int,
    ) -> None:
        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            initial_test_data.user,
        )
        episodes = [
            create_random_episode(session_scoped_session, channel_show.show)
            for _ in range(episode_count)
        ]
        self.assert_whitelist_success(
            session_scoped_client,
            initial_test_data.record,
            channel_show,
            episodes,
            initial_test_data.headers,
        )


@dataclass
class WhitelistUpdateTestData:
    user: User
    user_headers: dict[str, str]
    channel: Channel
    channel_show: ChannelShow
    preserved_marked_episode: Episode
    preserved_unmarked_episode: Episode
    target_episode: Episode
    initial_input: WhitelistShowInput


class TestUpdateWhitelist(BaseChannelSubEndpointTests):
    sub_http_method = "patch"
    sub_parameters = WhitelistShowInput(is_whitelist=True).model_dump(mode="json")

    def can_access_sub_endpoint(
        self,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
    ) -> bool:
        return user_is_authenticated and user_is_owner

    def sub_url(self, channel_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/{self.endpoint_name}/{channel_id}/whitelist/{uuid.uuid4()}"

    @staticmethod
    def assert_whitelist_state(
        result: WhitelistShowOutput,
        *,
        expected_mode: bool,
        expected_episode_ids: set[uuid.UUID],
        expected_season_ids: set[uuid.UUID],
    ) -> None:
        assert result.is_whitelist is expected_mode
        assert {e.id for e in result.episodes if e.filtered} == expected_episode_ids
        assert {s.id for s in result.seasons if s.filtered} == expected_season_ids

    def assert_update_result(
        self,
        session_scoped_client: TestClient,
        setup: WhitelistUpdateTestData,
        update_input: WhitelistShowInput,
        *,
        expected_mode: bool,
        expected_episode_ids: set[uuid.UUID],
        expected_season_ids: set[uuid.UUID],
    ) -> None:
        result = assert_success(
            client=session_scoped_client,
            method="patch",
            url=f"{settings.API_V1_STR}/channels/{setup.channel.id}/whitelist/{setup.channel_show.show_id}",
            output_schema=WhitelistShowOutput,
            headers=setup.user_headers,
            parameters=update_input.model_dump(mode="json"),
        )
        self.assert_whitelist_state(
            result,
            expected_mode=expected_mode,
            expected_episode_ids=expected_episode_ids,
            expected_season_ids=expected_season_ids,
        )

    def create_whitelist_test_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> WhitelistUpdateTestData:

        initial_test_data = self.create_test_data(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        channel_show = create_random_channel_show(
            session_scoped_session,
            initial_test_data.record,
            initial_test_data.user,
            is_whitelist=True,
        )
        episodes = [
            create_random_episode(session_scoped_session, channel_show.show)
            for _ in range(3)
        ]
        preserved_marked_episode = episodes[0]
        preserved_unmarked_episode = episodes[1]
        target_episode = episodes[2]

        seasons = [
            WhitelistEntryInput(id=preserved_marked_episode.season.id, marked=True),
            WhitelistEntryInput(id=preserved_unmarked_episode.season.id, marked=False),
        ]
        episodes_input = [
            WhitelistEntryInput(id=preserved_marked_episode.id, marked=True),
            WhitelistEntryInput(id=preserved_unmarked_episode.id, marked=False),
        ]
        seasons.append(WhitelistEntryInput(id=target_episode.season.id, marked=True))
        episodes_input.append(WhitelistEntryInput(id=target_episode.id, marked=True))
        initial_input = WhitelistShowInput(
            is_whitelist=True,
            seasons=seasons,
            episodes=episodes_input,
        )

        return WhitelistUpdateTestData(
            user=initial_test_data.user,
            user_headers=initial_test_data.headers,
            channel=initial_test_data.record,
            channel_show=channel_show,
            preserved_marked_episode=preserved_marked_episode,
            preserved_unmarked_episode=preserved_unmarked_episode,
            target_episode=target_episode,
            initial_input=initial_input,
        )

    def test_update_whitelist_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = self.create_whitelist_test_data(
            session_scoped_client,
            session_scoped_session,
        )
        update_whitelist(
            session_scoped_session,
            setup.channel_show,
            setup.initial_input,
        )

        update_input = WhitelistShowInput(
            is_whitelist=True,
            seasons=[
                WhitelistEntryInput(
                    id=setup.preserved_unmarked_episode.season.id,
                    marked=True,
                ),
                WhitelistEntryInput(id=setup.target_episode.season.id, marked=False),
            ],
            episodes=[
                WhitelistEntryInput(
                    id=setup.preserved_unmarked_episode.id,
                    marked=True,
                ),
                WhitelistEntryInput(id=setup.target_episode.id, marked=False),
            ],
        )
        expected_episode_ids = {
            setup.preserved_marked_episode.id,
            setup.preserved_unmarked_episode.id,
        }
        expected_season_ids = {
            setup.preserved_marked_episode.season.id,
            setup.preserved_unmarked_episode.season.id,
        }
        self.assert_update_result(
            session_scoped_client,
            setup,
            update_input,
            expected_mode=True,
            expected_episode_ids=expected_episode_ids,
            expected_season_ids=expected_season_ids,
        )
