# TODO: Validate

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import HTTPException, Path
from sqlmodel import Session, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.schemas import DELETABLE_MODELS, USER_OWNED_MODELS, Message
from app.users.dependencies import OptionalUser


# TODO: Validate
def readable_record[T: USER_OWNED_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if readable by the user."""

    # TODO: Validate
    def dependency(
        session: SessionDep,
        optional_user: OptionalUser,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if result := session.exec(select(model).where(model.id == record_id)).first():
            if result.is_publically_readable(session):
                return result
            if optional_user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            record_user_id = result.owner_id(session)
            if optional_user.is_superuser or optional_user.id == record_user_id:
                return result
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to access this {model.__name__}",
            )
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


# TODO: Validate
def editable_record[T: USER_OWNED_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if owned by the user."""

    # TODO: Validate
    def dependency(
        session: SessionDep,
        current_user: CurrentUser,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if record := session.exec(select(model).where(model.id == record_id)).first():
            record_user_id = record.owner_id(session)
            if current_user.is_superuser or current_user.id == record_user_id:
                return record
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to access this {model.__name__}",
            )
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


# TODO: Validate
def existing_record[T: DELETABLE_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if it exists.

    Unlike `owned_record`/`readable_record` this performs no authorization check, so
    routes using it must guard access separately (e.g. `get_current_active_superuser`).
    """

    # TODO: Validate
    def dependency(
        session: SessionDep,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if record := session.exec(select(model).where(model.id == record_id)).first():
            return record
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


# TODO: Validate
def delete_record(
    session: Session,
    existing_record: DELETABLE_MODELS,
) -> Message:
    """Delete the record and return a success message."""
    session.delete(existing_record)
    session.commit()
    return Message(message=f"{type(existing_record).__name__} deleted successfully")
