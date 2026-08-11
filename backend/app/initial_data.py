# TODO: Validate
import logging

from sqlmodel import Session

from app.database import engine, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# TODO: Validate
def init() -> None:
    with Session(engine) as session:
        init_db(session)


# TODO: Validate
def main() -> None:
    logger.info("Creating initial data")
    init()
    logger.info("Initial data created")


if __name__ == "__main__":
    main()
