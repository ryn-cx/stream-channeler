# TODO: Validate
from importlib import import_module

from sqlmodel import Session, create_engine, select

from app.config import settings
from app.constants import APP_PATH
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# TODO: Validate
def automatically_import_models() -> None:
    for model_file in APP_PATH.glob("*/models.py"):
        import_module(f"app.{model_file.parent.name}.models")


# TODO: Validate
def load_models() -> None:
    automatically_import_models()


# TODO: Update this comment upstream.
# TODO: Validate
def init_db(session: Session) -> None:
    # make sure all SQLModel models are imported before initializing DB otherwise,
    # SQLModel might fail to initialize relationships properly for more details:
    # https://github.com/fastapi/full-stack-fastapi-template/issues/28
    load_models()

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER),
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            username=settings.FIRST_SUPERUSER_USERNAME,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = user_service.create_user(session=session, user_create=user_in)
