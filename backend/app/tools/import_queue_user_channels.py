# TODO: Validate

from loguru import logger

from app.database import load_models
from app.log import configure_logging
from app.tools.import_queue import run_forever

logger = logger.bind(source="import_queue_user_channels")

if __name__ == "__main__":
    configure_logging()
    load_models()
    run_forever(skip_plugin_user_channels=True)
    logger.info("Import queue process stopped")
