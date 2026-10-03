# TODO: Validate
from typing import Annotated

from fastapi import Depends, Request
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.database import engine
from app.user_actions.models import UserAction, UserActionKind
from app.users.dependencies import OptionalUser
from app.users.models import User


# TODO: Validate
class ActionRecorder:
    # TODO: Validate
    def __init__(self, request: Request, user: User | None) -> None:
        self.user = user
        self.ip_address = request.headers.get("cf-connecting-ip") or (
            request.client.host if request.client else None
        )

    # TODO: Validate
    def record(self, kind: UserActionKind, **details: object) -> None:
        with Session(engine) as session:
            session.add(
                UserAction(
                    user_id=self.user.id if self.user else None,
                    ip_address=self.ip_address,
                    action=kind,
                    details=jsonable_encoder(details),
                ),
            )
            session.commit()


# TODO: Validate
def get_action_recorder(request: Request, user: OptionalUser) -> ActionRecorder:
    return ActionRecorder(request, user)


ActionLog = Annotated[ActionRecorder, Depends(get_action_recorder)]
