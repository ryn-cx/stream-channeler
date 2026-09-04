# TODO: Validate
"""What the user service does once a request has been let through."""

import uuid

import pytest
from fastapi import HTTPException, status
from sqlmodel import Session

from app.auth.schemas import UpdatePassword
from app.auth.security import verify_password
from app.sources.service.lookup import OTHER_SOURCE_KEY
from app.users.schemas import (
    SourcePreference,
    UserCreate,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
)
from app.users.service import accounts, administration, preferences
from tests.app.helpers.utils import random_email, random_lower_string
from tests.app.users.utils import (
    TEST_PASSWORD,
    create_random_superuser,
    create_random_user,
)


# TODO: Validate
def test_register_user_stores_the_account(session_scoped_session: Session) -> None:
    email = random_email()
    user = accounts.register_user(
        session_scoped_session,
        UserRegister(
            email=email,
            username=random_lower_string(),
            password=random_lower_string(),
        ),
    )
    assert user.email == email
    assert session_scoped_session.get(type(user), user.id) is user


# TODO: Validate
def test_register_user_refuses_an_email_already_taken(
    session_scoped_session: Session,
) -> None:
    existing = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.register_user(
            session_scoped_session,
            UserRegister(
                email=existing.email,
                username=random_lower_string(),
                password=random_lower_string(),
            ),
        )
    assert error.value.status_code == status.HTTP_400_BAD_REQUEST


# TODO: Validate
def test_register_user_refuses_a_username_already_taken(
    session_scoped_session: Session,
) -> None:
    existing = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.register_user(
            session_scoped_session,
            UserRegister(
                email=random_email(),
                username=existing.username,
                password=random_lower_string(),
            ),
        )
    assert error.value.status_code == status.HTTP_400_BAD_REQUEST


# TODO: Validate
def test_update_own_user_writes_the_new_name(session_scoped_session: Session) -> None:
    user = create_random_user(session_scoped_session)
    username = random_lower_string()
    updated = accounts.update_own_user(
        session_scoped_session,
        user,
        UserUpdateMe(username=username),
    )
    assert updated.username == username


# TODO: Validate
def test_update_own_user_refuses_an_email_another_user_has(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    other = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.update_own_user(
            session_scoped_session,
            user,
            UserUpdateMe(email=other.email),
        )
    assert error.value.status_code == status.HTTP_409_CONFLICT


# TODO: Validate
def test_change_own_password_replaces_the_hash(session_scoped_session: Session) -> None:
    user = create_random_user(session_scoped_session)
    new_password = random_lower_string()
    accounts.change_own_password(
        session_scoped_session,
        user,
        UpdatePassword(current_password=TEST_PASSWORD, new_password=new_password),
    )
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified


# TODO: Validate
def test_change_own_password_refuses_the_wrong_current_password(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.change_own_password(
            session_scoped_session,
            user,
            UpdatePassword(
                current_password=random_lower_string(),
                new_password=random_lower_string(),
            ),
        )
    assert error.value.status_code == status.HTTP_400_BAD_REQUEST


# TODO: Validate
def test_change_own_password_refuses_the_same_password(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.change_own_password(
            session_scoped_session,
            user,
            UpdatePassword(
                current_password=TEST_PASSWORD,
                new_password=TEST_PASSWORD,
            ),
        )
    assert error.value.status_code == status.HTTP_400_BAD_REQUEST


# TODO: Validate
def test_delete_own_user_removes_the_account(session_scoped_session: Session) -> None:
    user = create_random_user(session_scoped_session)
    user_id = user.id
    accounts.delete_own_user(session_scoped_session, user)
    assert accounts.readable_user is not None
    assert session_scoped_session.get(type(user), user_id) is None


# TODO: Validate
def test_delete_own_user_refuses_a_superuser(session_scoped_session: Session) -> None:
    admin = create_random_superuser(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.delete_own_user(session_scoped_session, admin)
    assert error.value.status_code == status.HTTP_403_FORBIDDEN


# TODO: Validate
def test_readable_user_gives_a_user_themselves(session_scoped_session: Session) -> None:
    user = create_random_user(session_scoped_session)
    assert accounts.readable_user(session_scoped_session, user, user.id) is user


# TODO: Validate
def test_readable_user_refuses_a_stranger(session_scoped_session: Session) -> None:
    subject = create_random_user(session_scoped_session)
    stranger = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.readable_user(session_scoped_session, stranger, subject.id)
    assert error.value.status_code == status.HTTP_403_FORBIDDEN


# TODO: Validate
def test_readable_user_tells_an_admin_when_nobody_is_there(
    session_scoped_session: Session,
) -> None:
    admin = create_random_superuser(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        accounts.readable_user(session_scoped_session, admin, uuid.uuid4())
    assert error.value.status_code == status.HTTP_404_NOT_FOUND


# TODO: Validate
def test_source_preferences_always_end_with_other(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    outputs = preferences.source_preferences_output(session_scoped_session, user)
    assert outputs[-1].source_key == OTHER_SOURCE_KEY


# TODO: Validate
def test_replace_source_preferences_keeps_the_order_given(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    stored = preferences.replace_source_preferences(
        session_scoped_session,
        user,
        [SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=False)],
    )
    assert stored[0].source_key == OTHER_SOURCE_KEY
    assert stored[0].enabled is False


# TODO: Validate
def test_replace_source_preferences_refuses_an_unknown_source(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        preferences.replace_source_preferences(
            session_scoped_session,
            user,
            [SourcePreference(source_key=random_lower_string(), enabled=True)],
        )
    assert error.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# TODO: Validate
def test_replace_source_preferences_refuses_a_duplicate(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        preferences.replace_source_preferences(
            session_scoped_session,
            user,
            [
                SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=True),
                SourcePreference(source_key=OTHER_SOURCE_KEY, enabled=True),
            ],
        )
    assert error.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# TODO: Validate
def test_create_user_as_admin_refuses_an_email_already_taken(
    session_scoped_session: Session,
) -> None:
    existing = create_random_user(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        administration.create_user_as_admin(
            session_scoped_session,
            UserCreate(
                email=existing.email,
                username=random_lower_string(),
                password=random_lower_string(),
            ),
        )
    assert error.value.status_code == status.HTTP_400_BAD_REQUEST


# TODO: Validate
def test_update_user_as_admin_writes_the_change(
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    email = random_email()
    updated = administration.update_user_as_admin(
        session_scoped_session,
        user,
        UserUpdate(email=email),
    )
    assert updated.email == email


# TODO: Validate
def test_delete_user_as_admin_refuses_the_admin_themselves(
    session_scoped_session: Session,
) -> None:
    admin = create_random_superuser(session_scoped_session)
    with pytest.raises(HTTPException) as error:
        administration.delete_user_as_admin(session_scoped_session, admin, admin)
    assert error.value.status_code == status.HTTP_403_FORBIDDEN


# TODO: Validate
def test_delete_user_as_admin_removes_another_user(
    session_scoped_session: Session,
) -> None:
    admin = create_random_superuser(session_scoped_session)
    subject = create_random_user(session_scoped_session)
    subject_id = subject.id
    administration.delete_user_as_admin(session_scoped_session, admin, subject)
    assert session_scoped_session.get(type(subject), subject_id) is None


# TODO: Validate
def test_list_users_counts_every_account(session_scoped_session: Session) -> None:
    before = administration.list_users(session_scoped_session, 0, 100_000).count
    create_random_user(session_scoped_session)
    after = administration.list_users(session_scoped_session, 0, 100_000).count
    assert after == before + 1
