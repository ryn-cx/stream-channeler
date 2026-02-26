# TODO: Validate

from pathlib import Path

from loguru import logger
from pyinstrument import Profiler
from sqlmodel import Session

from app.database import engine, load_models
from app.plugins.utils.manage_plugins import import_plugins, plugins

import_plugins()
load_models()


def reimport_single_url(session: Session) -> None:
    url = "https://www.youtube.com/channel/UC58IKuPHnZkdCZ6T5mSRGCg"

    for plugin in plugins:
        if plugin.is_valid_url_format(url):
            plugin_instance = plugin(session)
            plugin_instance.import_url(url)


if __name__ == "__main__":
    profiler = Profiler()
    profiler.start()

    with Session(engine) as session:
        reimport_single_url(session)

    profiler.stop()

    # Output HTML flamegraph
    html_output_path = Path("temp.html")
    html_output_path.write_text(
        profiler.output_html(),
        encoding="utf-8",
    )
    logger.info(f"Flamegraph saved to {html_output_path}")

    # Also output text to console
    logger.info(
        f"Profile results:\n{profiler.output_text(unicode=True, color=True)}",
    )
