# TODO: Validate
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from sqlmodel import Session, select

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

from app.database import engine, load_models
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.utils import tz_datetime
from app.watches.models import Watch

load_models()

INPUTS_DIR = Path(__file__).parent / "inputs"
PLUGIN_KEY = "Crunchyroll"


def load_watch_history() -> list[dict[str, object]]:
    """Load all watch history entries from the input JSON files."""
    entries: list[dict[str, object]] = []
    for json_file in sorted(INPUTS_DIR.glob("*.json")):
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)
        entries.extend(data["data"])
    return entries


def import_watches(session: Session, user: User) -> None:
    plugin = Plugin.get(session, PLUGIN_KEY, user)
    if not plugin:
        logger.warning(f"Plugin '{PLUGIN_KEY}' not found in database")
        return

    # Load all Crunchyroll episodes keyed by their episode key
    episodes_by_key: dict[str, Episode] = {}
    statement = (
        select(Episode)
        .join(Season)
        .join(Show)
        .join(Source)
        .where(Source.plugin_id == plugin.id)
    )
    for episode in session.exec(statement):
        episodes_by_key[episode.key] = episode

    # Load existing watches for this user to avoid duplicates
    existing_watches: set[tuple[str, datetime]] = set()
    watch_statement = select(Watch).where(Watch.user_id == user.id)
    for watch in session.exec(watch_statement):
        existing_watches.add((str(watch.episode_id), watch.watch_date))

    entries = load_watch_history()
    added = 0
    skipped_not_found = 0
    skipped_already_watched = 0

    for entry in entries:
        episode_key = str(entry["id"])
        episode = episodes_by_key.get(episode_key)
        if not episode:
            skipped_not_found += 1
            continue

        watch_date = tz_datetime.fromisoformat(str(entry["date_played"]))
        if (str(episode.id), watch_date) in existing_watches:
            skipped_already_watched += 1
            continue

        episode_watch = Watch(
            user_id=user.id,
            episode_id=episode.id,
            watch_date=watch_date,
            verified=True,
        )
        session.add(episode_watch)
        existing_watches.add((str(episode.id), watch_date))
        added += 1

    session.commit()
    logger.info(
        f"Watch import complete: {added} added, "
        f"{skipped_already_watched} already watched, "
        f"{skipped_not_found} not found in database",
    )


if __name__ == "__main__":
    with Session(engine) as session:
        user = session.exec(select(User)).all()[1]
        if not user:
            logger.error("No user found in database")
        else:
            logger.info(f"Importing watch history for user: {user.email}")
            import_watches(session, user)
