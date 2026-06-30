# TODO: Validate
from importlib import import_module

from sqlmodel import Session, create_engine, select

from app.config import settings
from app.constants import APP_PATH
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def automatically_import_models() -> None:
    for model_file in APP_PATH.glob("*/models.py"):
        import_module(f"app.{model_file.parent.name}.models")


def init_db(session: Session) -> None:
    # make sure all SQLModel models are imported before initializing DB otherwise,
    # SQLModel might fail to initialize relationships properly for more details:
    # https://github.com/fastapi/full-stack-fastapi-template/issues/28
    automatically_import_models()

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER),
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = user_service.create_user(session=session, user_create=user_in)
