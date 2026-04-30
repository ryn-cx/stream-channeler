# TODO: Validate
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

if TYPE_CHECKING:
    from app.users.models import User

from app.schemas import MediaModel, Message


def get_first_owned_record_or_error[T: MediaModel](
    session: Session,
    statement: SelectOfScalar[T],
    current_user_id: uuid.UUID,
    name: str,
) -> T:
    """Get a record if it is owned by the current user or raise an error.

    Raises:
        403 if authenticated but not owner
        404 if record not found
    """
    if result := session.exec(statement).first():
        if result.get_user_id(session) != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access this {name}",
            )
        return result
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{name} not found",
    )


def get_first_readable_record_or_error[T: MediaModel](
    session: Session,
    statement: SelectOfScalar[T],
    current_user_id: uuid.UUID | None,
    name: str,
) -> T:
    """Get a record if it is readable by the current user or raise an error.

    Raises:
        401 if not authenticated and record is not public
        403 if authenticated but not owner and record is not public
        404 if record not found
    """
    if result := session.exec(statement).first():
        if result.is_public(session):
            return result
        if current_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        if result.get_user_id(session) != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to access this {name}",
            )
        return result
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{name} not found",
    )


def get_owned_record[T: MediaModel](
    session: Session,
    model: type[T],
    resource_id: uuid.UUID,
    current_user_id: uuid.UUID,
) -> T:
    """Get a record if it is owned by the current user."""
    statement = select(model).where(model.id == resource_id)
    return get_first_owned_record_or_error(
        session,
        statement,
        current_user_id,
        model.__name__,
    )


def get_readable_record[T: MediaModel](
    session: Session,
    model: type[T],
    resource_id: uuid.UUID,
    user: User | None,
) -> T:
    """Get a record if it is readable by the current user."""
    statement = select(model).where(model.id == resource_id)
    user_id = user.id if user else None
    return get_first_readable_record_or_error(
        session,
        statement,
        user_id,
        model.__name__,
    )


def raise_if_exists(
    existing: MediaModel | None,
) -> None:
    """Raise 409 Conflict if a record already exists."""
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{type(existing).__name__} with this key already exists",
        )


def delete_record(
    session: Session,
    existing_record: MediaModel,
) -> Message:
    """Remove record, commit, and return a success message."""
    session.delete(existing_record)
    session.commit()
    return Message(message=f"{type(existing_record).__name__} deleted successfully")
