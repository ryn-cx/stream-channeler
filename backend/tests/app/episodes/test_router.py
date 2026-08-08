# TODO: Validate

import dataclasses
import uuid
from collections.abc import Sequence
from typing import Literal

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, select

from app.config import settings
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeUpdate,
)
from app.models import Visibility
from app.users.models import User
from tests.app.episodes.utils import create_random_episode
from tests.app.users.utils import (
    authentication_token_from_email,
    create_random_superuser,
    create_random_user,
)
from tests.app.utils.utils import build_random_model, request_payload


@dataclasses.dataclass
class EpisodeSetup:
    episode: Episode
    user: User
    headers: dict[str, str]


def episode_url(episode_id: uuid.UUID | str) -> str:
    return f"{settings.API_V1_STR}/episodes/{episode_id}"


def season_episodes_url(season_id: uuid.UUID | str) -> str:
    return f"{settings.API_V1_STR}/seasons/{season_id}/episodes"


def set_up_episode(  # noqa: PLR0913 - the permission axes are the point of the setup
    client: TestClient,
    session: Session,
    *,
    user_is_owner: bool,
    user_is_authenticated: bool,
    record_is_public: bool,
    user_is_superuser: bool = False,
) -> EpisodeSetup:
    user = (
        create_random_superuser(session)
        if user_is_superuser
        else create_random_user(session)
    )
    other_user = create_random_user(session)

    owner = user if user_is_owner else other_user
    episode = create_random_episode(session, owner.id)

    # Unrelated episodes, so a route that returns the wrong records is caught.
    create_random_episode(session, user.id)
    create_random_episode(session, other_user.id)

    episode.season.show.source.plugin.visibility = (
        Visibility.public if record_is_public else Visibility.private
    )
    session.flush()

    headers = (
        authentication_token_from_email(
            client=client,
            email=user.email,
            session=session,
        )
        if user_is_authenticated
        else {}
    )
    return EpisodeSetup(episode=episode, user=user, headers=headers)


def all_episodes(session: Session) -> Sequence[Episode]:
    return session.exec(select(Episode)).all()


def episode_from_database(session: Session, episode_id: uuid.UUID) -> Episode:
    return session.exec(select(Episode).where(Episode.id == episode_id)).one()


def assert_denied(
    response: Response,
    *,
    user_is_authenticated: bool,
    model_name: str,
) -> None:
    if user_is_authenticated:
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert (
            response.json()["detail"] == f"Not authorized to access this {model_name}"
        )
    else:
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


def assert_saved_to_database(session: Session, episode: EpisodeOutput) -> None:
    record = episode_from_database(session, episode.id)
    assert EpisodeOutput.model_validate(record).model_dump() == episode.model_dump()


class TestCreateEpisode:
    @pytest.mark.parametrize("user_is_superuser", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    @pytest.mark.parametrize("record_is_public", [True, False])
    def test_create_permissions(  # noqa: PLR0913 - parametrize axes
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )
        season = setup.episode.season
        # Create against an empty season, so nothing already under it matters.
        session_scoped_session.delete(setup.episode)
        session_scoped_session.flush()

        episodes_before = all_episodes(session_scoped_session)
        response = session_scoped_client.post(
            season_episodes_url(season.id),
            json=request_payload(build_random_model(EpisodeCreate)),
            headers=setup.headers,
        )

        can_create = user_is_authenticated and (user_is_owner or user_is_superuser)
        if can_create:
            assert response.status_code == status.HTTP_200_OK
            created = EpisodeOutput.model_validate(response.json())
            assert created.season_id == season.id
            assert_saved_to_database(session_scoped_session, created)
        else:
            assert_denied(
                response,
                user_is_authenticated=user_is_authenticated,
                model_name="Season",
            )
            assert all_episodes(session_scoped_session) == episodes_before

    @pytest.mark.parametrize("mode", ["full", "minimal"])
    def test_create_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        mode: Literal["full", "minimal"],
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        season = setup.episode.season
        session_scoped_session.delete(setup.episode)
        session_scoped_session.flush()

        episode_input = build_random_model(EpisodeCreate, mode)
        response = session_scoped_client.post(
            season_episodes_url(season.id),
            json=request_payload(episode_input),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        created = EpisodeOutput.model_validate(response.json())
        assert (
            episode_input.model_dump(exclude_unset=True).items()
            <= created.model_dump().items()
        )
        assert_saved_to_database(session_scoped_session, created)

    @pytest.mark.parametrize("existing_episode_count", [1, 2])
    def test_create_with_existing_episodes(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        existing_episode_count: int,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        season = setup.episode.season
        for _ in range(existing_episode_count - 1):
            create_random_episode(session_scoped_session, season)

        response = session_scoped_client.post(
            season_episodes_url(season.id),
            json=request_payload(build_random_model(EpisodeCreate)),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        created = EpisodeOutput.model_validate(response.json())
        assert_saved_to_database(session_scoped_session, created)
        siblings = session_scoped_session.exec(
            select(Episode).where(Episode.season_id == season.id),
        ).all()
        assert len(siblings) == existing_episode_count + 1

    def test_create_shared_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        other_user = create_random_user(session_scoped_session)
        other_episode = create_random_episode(session_scoped_session, other_user.id)

        response = session_scoped_client.post(
            season_episodes_url(setup.episode.season_id),
            json=request_payload(
                build_random_model(EpisodeCreate, key=other_episode.key),
            ),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        created = EpisodeOutput.model_validate(response.json())
        assert created.key == other_episode.key
        assert_saved_to_database(session_scoped_session, created)

    def test_create_duplicate_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.post(
            season_episodes_url(setup.episode.season_id),
            json=request_payload(
                build_random_model(EpisodeCreate, key=setup.episode.key),
            ),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Episode with this key already exists"
        assert all_episodes(session_scoped_session) == episodes_before

    def test_create_season_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.post(
            season_episodes_url(uuid.uuid4()),
            json=request_payload(build_random_model(EpisodeCreate)),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Season not found"
        assert all_episodes(session_scoped_session) == episodes_before


class TestGetEpisodes:
    @pytest.mark.parametrize("user_is_superuser", [True, False])
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_list_permissions(  # noqa: PLR0913 - parametrize axes
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )
        season = setup.episode.season

        response = session_scoped_client.get(
            season_episodes_url(season.id),
            headers=setup.headers,
        )

        can_read = record_is_public or (
            user_is_authenticated and (user_is_owner or user_is_superuser)
        )
        if can_read:
            assert response.status_code == status.HTTP_200_OK
            returned = EpisodesPublic.model_validate(response.json())
            assert [item.id for item in returned.data] == [setup.episode.id]
        else:
            assert_denied(
                response,
                user_is_authenticated=user_is_authenticated,
                model_name="Season",
            )

    @pytest.mark.parametrize("episode_count", [0, 1, 2])
    def test_list_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        episode_count: int,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        season = setup.episode.season
        session_scoped_session.delete(setup.episode)
        session_scoped_session.flush()
        for _ in range(episode_count):
            create_random_episode(session_scoped_session, season)

        response = session_scoped_client.get(
            season_episodes_url(season.id),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        returned = EpisodesPublic.model_validate(response.json())
        records = session_scoped_session.exec(
            select(Episode).where(Episode.season_id == season.id),
        ).all()
        assert len(returned.data) == episode_count
        assert returned.total_count == episode_count

        returned_by_id = {item.id: item for item in returned.data}
        for record in records:
            expected = EpisodeOutput.model_validate(record).model_dump()
            assert expected.items() <= returned_by_id[record.id].model_dump().items()


class TestUpdateEpisode:
    @pytest.mark.parametrize("user_is_superuser", [True, False])
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_update_permissions(  # noqa: PLR0913 - parametrize axes
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.patch(
            episode_url(setup.episode.id),
            json=request_payload(build_random_model(EpisodeUpdate)),
            headers=setup.headers,
        )

        can_update = user_is_authenticated and (user_is_owner or user_is_superuser)
        if can_update:
            assert response.status_code == status.HTTP_200_OK
            updated = EpisodeOutput.model_validate(response.json())
            assert updated.id == setup.episode.id
            assert_saved_to_database(session_scoped_session, updated)
        else:
            assert_denied(
                response,
                user_is_authenticated=user_is_authenticated,
                model_name="Episode",
            )
            assert all_episodes(session_scoped_session) == episodes_before

    @pytest.mark.parametrize("update_mode", ["full", "minimal"])
    @pytest.mark.parametrize("create_mode", ["full", "minimal"])
    def test_update_data(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        create_mode: Literal["full", "minimal"],
        update_mode: Literal["full", "minimal"],
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        setup.episode.sqlmodel_update(
            build_random_model(EpisodeUpdate, create_mode).model_dump(
                exclude_unset=True,
            ),
        )
        session_scoped_session.flush()
        original = EpisodeOutput.model_validate(setup.episode).model_dump()
        original_modified_at = setup.episode.modified_at

        update_input = build_random_model(EpisodeUpdate, update_mode)
        response = session_scoped_client.patch(
            episode_url(setup.episode.id),
            json=request_payload(update_input),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        record = episode_from_database(session_scoped_session, setup.episode.id)
        expected = original | update_input.model_dump(exclude_unset=True)
        assert EpisodeOutput.model_validate(record).model_dump() == expected
        assert record.modified_at >= original_modified_at

    def test_update_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=True,
        )
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.patch(
            episode_url(uuid.uuid4()),
            json=request_payload(build_random_model(EpisodeUpdate)),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Episode not found"
        assert all_episodes(session_scoped_session) == episodes_before

    def test_update_shared_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        other_user = create_random_user(session_scoped_session)
        create_random_episode(
            session_scoped_session,
            other_user.id,
            key=setup.episode.key,
        )

        response = session_scoped_client.patch(
            episode_url(setup.episode.id),
            json=request_payload(build_random_model(EpisodeUpdate)),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert_saved_to_database(
            session_scoped_session,
            EpisodeOutput.model_validate(response.json()),
        )

    def test_update_duplicate_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        sibling = create_random_episode(session_scoped_session, setup.episode.season)
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.patch(
            episode_url(setup.episode.id),
            json=request_payload(build_random_model(EpisodeUpdate, key=sibling.key)),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json()["detail"] == "Episode with this key already exists"
        assert all_episodes(session_scoped_session) == episodes_before

    def test_update_rejects_empty_key(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        parameters = request_payload(build_random_model(EpisodeUpdate))
        parameters["key"] = ""
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.patch(
            episode_url(setup.episode.id),
            json=parameters,
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert all_episodes(session_scoped_session) == episodes_before

    def test_update_resists_injecting_id(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        parameters = request_payload(build_random_model(EpisodeUpdate))
        parameters["id"] = str(uuid.uuid4())
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.patch(
            episode_url(setup.episode.id),
            json=parameters,
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert all_episodes(session_scoped_session) == episodes_before


class TestDeleteEpisode:
    @pytest.mark.parametrize("user_is_superuser", [True, False])
    @pytest.mark.parametrize("record_is_public", [True, False])
    @pytest.mark.parametrize("user_is_authenticated", [True, False])
    @pytest.mark.parametrize("user_is_owner", [True, False])
    def test_delete_permissions(  # noqa: PLR0913 - parametrize axes
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
        *,
        user_is_authenticated: bool,
        user_is_owner: bool,
        record_is_public: bool,
        user_is_superuser: bool,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=user_is_owner,
            user_is_authenticated=user_is_authenticated,
            record_is_public=record_is_public,
            user_is_superuser=user_is_superuser,
        )
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.delete(
            episode_url(setup.episode.id),
            headers=setup.headers,
        )

        can_delete = user_is_authenticated and (user_is_owner or user_is_superuser)
        if can_delete:
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["message"] == "Episode deleted successfully"
            assert not session_scoped_session.exec(
                select(Episode).where(Episode.id == setup.episode.id),
            ).first()
        else:
            assert_denied(
                response,
                user_is_authenticated=user_is_authenticated,
                model_name="Episode",
            )
            assert all_episodes(session_scoped_session) == episodes_before

    def test_delete_not_found(
        self,
        session_scoped_client: TestClient,
        session_scoped_session: Session,
    ) -> None:
        setup = set_up_episode(
            session_scoped_client,
            session_scoped_session,
            user_is_owner=True,
            user_is_authenticated=True,
            record_is_public=False,
        )
        episodes_before = all_episodes(session_scoped_session)

        response = session_scoped_client.delete(
            episode_url(uuid.uuid4()),
            headers=setup.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Episode not found"
        assert all_episodes(session_scoped_session) == episodes_before
