# TODO: Validate


import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.models import Visibility
from app.playlists.models import Playlist, PlaylistEpisode
from app.playlists.schemas import (
    PlaylistCreate,
    PlaylistDetailOutput,
    PlaylistEpisodesOutput,
    PlaylistEpisodeWithExtrasOutput,
    PlaylistOutput,
    PlaylistUpdate,
)
from app.plugins.schemas import PluginOutput
from app.seasons.schemas import SeasonOutput
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.watches.models import Watch
from tests.app.episodes.utils import create_random_episode
from tests.app.playlists.utils import (
    create_random_playlist,
    create_random_playlist_episode,
)
from tests.app.users.utils import authentication_token_from_email, create_random_user
from tests.app.utils.base import (
    CREATE_SCHEMAS,
    OUTPUT_SCHEMAS,
    BaseTests,
    CreatedTestData,
)
from tests.app.utils.base_create import UserOwnedCreateMixin
from tests.app.utils.base_delete import BaseDeleteTests
from tests.app.utils.base_get import UserOwnedGetMixin
from tests.app.utils.base_update import BaseUpdateTests
from tests.app.utils.route_assertions import (
    Method,
    assert_forbidden,
    assert_not_authenticated,
    assert_not_found,
    assert_success,
    make_request,
)
from tests.app.utils.utils import random_lower_string


def _scrub_episode_ids[T: PlaylistCreate | PlaylistUpdate](model: T) -> T:
    """Drop `episode_ids` from a randomly-built playlist input.

    `build_random_model` populates this list with random UUIDs that do not
    correspond to any episode, which the API rejects with 400. The base test
    framework has no awareness of FK-validated list fields, so playlist-specific
    create/update assertions strip this field before sending the request.
    """
    model.__pydantic_fields_set__.discard("episode_ids")
    return model


class PlaylistTestMixin(BaseTests[Playlist]):
    database_model = Playlist
    create_schema = PlaylistCreate
    output_schema = PlaylistOutput
    update_schema = PlaylistUpdate
    create_record_function = staticmethod(create_random_playlist)

    # Playlists do not rely on plugins for visibility and instead have their own public
    # field.
    def set_visibility(self, record: Playlist, *, record_is_public: bool) -> None:
        record.visibility = (
            Visibility.public if record_is_public else Visibility.private
        )


class TestCreatePlaylist(PlaylistTestMixin, UserOwnedCreateMixin[Playlist]):
    def assert_create_record_success(
        self,
        client: TestClient,
        session_scoped_session: Session,
        parent_id: uuid.UUID | None,
        headers: dict[str, str],
        parameters_model: CREATE_SCHEMAS,
    ) -> OUTPUT_SCHEMAS:
        assert isinstance(parameters_model, PlaylistCreate)
        return super().assert_create_record_success(
            client,
            session_scoped_session,
            parent_id,
            headers,
            _scrub_episode_ids(parameters_model),
        )


class TestGetPlaylist(PlaylistTestMixin, UserOwnedGetMixin[Playlist]):
    pass


class TestUpdatePlaylist(PlaylistTestMixin, BaseUpdateTests[Playlist]):
    def assert_api_update_success(
        self,
        session_scoped_session: Session,
        client: TestClient,
        setup: CreatedTestData[Playlist],
        patch_input: PlaylistUpdate,  # type: ignore[override]
    ) -> list[PlaylistOutput]:
        return super().assert_api_update_success(
            session_scoped_session,
            client,
            setup,
            _scrub_episode_ids(patch_input),  # type: ignore[arg-type]
        )


class TestDeletePlaylist(PlaylistTestMixin, BaseDeleteTests[Playlist]):
    pass


class BasePlaylistSubEndpointTests(PlaylistTestMixin):
    sub_http_method: Method
    sub_parameters: dict[str, object] | list[object] | None = None

    def sub_url(self, playlist_id: uuid.UUID) -> str:
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


class TestPlaylistEpisodes(BasePlaylistSubEndpointTests):
    sub_http_method = "get"
    sub_parameters = None

    def sub_url(self, playlist_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/playlists/{playlist_id}/episodes"

    @pytest.mark.skip(reason="Covered by test_with_episodes and test_no_episodes")
    def test_get_permissions(self) -> None:  # type: ignore[override]
        pass

    def generic_record_url(self, record_id: uuid.UUID | str) -> str:
        return f"{settings.API_V1_STR}/playlists/{record_id}/episodes"

    @staticmethod
    def create_playlist_with_episodes(
        session_scoped_session: Session,
        user_id: uuid.UUID,
        *,
        public: bool,
    ) -> tuple[Playlist, PlaylistEpisodesOutput]:
        playlist = create_random_playlist(
            session_scoped_session,
            user_id,
            visibility=Visibility.public if public else Visibility.private,
        )

        expected = PlaylistEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
        )

        for position in range(2):
            episode = create_random_episode(session_scoped_session)
            create_random_playlist_episode(
                session_scoped_session,
                playlist,
                position=position,
                episode=episode,
            )
            season = episode.season
            show = season.show
            source = show.source
            plugin = source.plugin

            expected.episodes.append(
                PlaylistEpisodeWithExtrasOutput(
                    **episode.model_dump(),
                    position=position,
                ),
            )
            expected.seasons[season.id] = SeasonOutput.model_validate(season)
            expected.shows[show.id] = ShowPublic.model_validate(show)
            expected.sources[source.id] = SourcePublic.model_validate(source)
            expected.plugins[plugin.id] = PluginOutput.model_validate(plugin)

        session_scoped_session.refresh(playlist)
        return playlist, expected

    @staticmethod
    def assert_episodes(
        response_data: PlaylistEpisodesOutput,
        expected: PlaylistEpisodesOutput,
    ) -> None:
        response_data.episodes.sort(key=lambda e: e.position)
        expected.episodes.sort(key=lambda e: e.position)
        assert response_data.episodes == expected.episodes
        assert response_data.seasons == expected.seasons
        assert response_data.shows == expected.shows
        assert response_data.sources == expected.sources
        assert response_data.plugins == expected.plugins
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
        playlist, expected = self.create_playlist_with_episodes(
            session_scoped_session,
            owner.id,
            public=record_is_public,
        )

        if not user_is_authenticated and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(playlist.id),
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
                url=self.generic_record_url(playlist.id),
                detail="Not authorized to access this Playlist",
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
            self.generic_record_url(playlist.id),
            headers=headers,
        )
        response_data = PlaylistEpisodesOutput.model_validate(response.json())

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
        playlist = create_random_playlist(
            session_scoped_session,
            owner.id,
            visibility=Visibility.public if record_is_public else Visibility.private,
        )
        expected = PlaylistEpisodesOutput(
            episodes=[],
            seasons={},
            shows={},
            sources={},
            plugins={},
        )

        if not user_is_authenticated and not record_is_public:
            assert_not_authenticated(
                client=session_scoped_client,
                method="get",
                url=self.generic_record_url(playlist.id),
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
                url=self.generic_record_url(playlist.id),
                detail="Not authorized to access this Playlist",
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
            self.generic_record_url(playlist.id),
            headers=headers,
        )
        response_data = PlaylistEpisodesOutput.model_validate(response.json())

        assert response.status_code == status.HTTP_200_OK
        assert response_data == expected

    def test_includes_viewer_watches_only(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        """The latest watch is hydrated for the current viewer, not other users."""
        owner = create_random_user(session_scoped_session)
        playlist = create_random_playlist(
            session_scoped_session,
            owner.id,
            visibility=Visibility.public,
        )
        episode = create_random_episode(session_scoped_session)
        create_random_playlist_episode(
            session_scoped_session,
            playlist,
            position=0,
            episode=episode,
        )

        viewer = create_random_user(session_scoped_session)
        viewer_headers = authentication_token_from_email(
            client=session_scoped_client,
            email=viewer.email,
            session=session_scoped_session,
        )

        # Another user's watch must not bleed into the viewer's response.
        other = create_random_user(session_scoped_session)
        session_scoped_session.add(
            Watch(user_id=other.id, episode_id=episode.id, verified=True),
        )
        session_scoped_session.flush()

        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=self.generic_record_url(playlist.id),
            output_schema=PlaylistEpisodesOutput,
            headers=viewer_headers,
        )
        assert result.episodes[0].watch_date is None
        assert result.episodes[0].verified is None
        assert result.episodes[0].episode_watch_id is None

        viewer_watch = Watch(
            user_id=viewer.id,
            episode_id=episode.id,
            verified=False,
        )
        session_scoped_session.add(viewer_watch)
        session_scoped_session.flush()

        result = assert_success(
            client=session_scoped_client,
            method="get",
            url=self.generic_record_url(playlist.id),
            output_schema=PlaylistEpisodesOutput,
            headers=viewer_headers,
        )
        assert result.episodes[0].watch_date is not None
        assert result.episodes[0].verified is False
        assert result.episodes[0].episode_watch_id == viewer_watch.id


class TestCreatePlaylistWithEpisodes(PlaylistTestMixin):
    """Custom create-path tests that exercise the `episode_ids` body field."""

    @staticmethod
    def url() -> str:
        return f"{settings.API_V1_STR}/playlists"

    def test_create_with_episodes_in_order(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        episodes = [create_random_episode(session_scoped_session) for _ in range(3)]

        result = assert_success(
            client=session_scoped_client,
            method="post",
            url=self.url(),
            output_schema=PlaylistDetailOutput,
            headers=headers,
            parameters={
                "visibility": Visibility.private,
                "episode_ids": [str(episode.id) for episode in episodes],
            },
        )

        assert result.user_id == user.id
        assert [entry.episode_id for entry in result.episodes] == [
            episode.id for episode in episodes
        ]
        assert [entry.position for entry in result.episodes] == [0, 1, 2]

    def test_create_unknown_episode(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )

        response = session_scoped_client.post(
            self.url(),
            headers=headers,
            json={
                "visibility": Visibility.private,
                "episode_ids": [str(uuid.uuid4())],
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unknown episode ids" in response.json()["detail"]


class TestUpdatePlaylistEpisodes(PlaylistTestMixin):
    """Custom update-path tests for the atomic `episode_ids` replacement."""

    @staticmethod
    def url(playlist_id: uuid.UUID) -> str:
        return f"{settings.API_V1_STR}/playlists/{playlist_id}"

    def test_update_replaces_episodes_atomically(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        playlist = create_random_playlist(session_scoped_session, user.id)
        old_episodes = [create_random_episode(session_scoped_session) for _ in range(2)]
        for index, episode in enumerate(old_episodes):
            create_random_playlist_episode(
                session_scoped_session,
                playlist,
                position=index,
                episode=episode,
            )

        new_episodes = [create_random_episode(session_scoped_session) for _ in range(3)]
        # Reverse the order so we know the new ordering is honoured rather than
        # preserved from the previous state.
        ordered_ids = [episode.id for episode in new_episodes][::-1]

        result = assert_success(
            client=session_scoped_client,
            method="patch",
            url=self.url(playlist.id),
            output_schema=PlaylistDetailOutput,
            headers=headers,
            parameters={"episode_ids": [str(eid) for eid in ordered_ids]},
        )

        assert [entry.episode_id for entry in result.episodes] == ordered_ids
        assert [entry.position for entry in result.episodes] == [0, 1, 2]

        remaining = session_scoped_session.exec(
            select(PlaylistEpisode).where(
                PlaylistEpisode.playlist_id == playlist.id,
            ),
        ).all()
        assert {entry.episode_id for entry in remaining} == set(ordered_ids)

    def test_update_omitting_episodes_preserves_them(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        playlist = create_random_playlist(session_scoped_session, user.id)
        episodes = [create_random_episode(session_scoped_session) for _ in range(2)]
        for index, episode in enumerate(episodes):
            create_random_playlist_episode(
                session_scoped_session,
                playlist,
                position=index,
                episode=episode,
            )

        result = assert_success(
            client=session_scoped_client,
            method="patch",
            url=self.url(playlist.id),
            output_schema=PlaylistDetailOutput,
            headers=headers,
            parameters={"name": random_lower_string()},
        )
        assert [entry.episode_id for entry in result.episodes] == [
            episode.id for episode in episodes
        ]

    def test_update_unknown_episode(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        playlist = create_random_playlist(session_scoped_session, user.id)

        response = session_scoped_client.patch(
            self.url(playlist.id),
            headers=headers,
            json={"episode_ids": [str(uuid.uuid4())]},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unknown episode ids" in response.json()["detail"]


class TestDeletePlaylistCascades(PlaylistTestMixin):
    """Verify that deleting a playlist removes its `PlaylistEpisode` rows."""

    def test_delete_removes_join_rows(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        user = create_random_user(session_scoped_session)
        headers = authentication_token_from_email(
            client=session_scoped_client,
            email=user.email,
            session=session_scoped_session,
        )
        playlist = create_random_playlist(session_scoped_session, user.id)
        episode = create_random_episode(session_scoped_session)
        create_random_playlist_episode(
            session_scoped_session,
            playlist,
            position=0,
            episode=episode,
        )

        response = session_scoped_client.delete(
            f"{settings.API_V1_STR}/playlists/{playlist.id}",
            headers=headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Playlist deleted successfully"

        remaining = session_scoped_session.exec(
            select(PlaylistEpisode).where(
                PlaylistEpisode.playlist_id == playlist.id,
            ),
        ).all()
        assert remaining == []
