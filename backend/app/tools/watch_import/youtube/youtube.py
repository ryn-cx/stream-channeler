# TODO: Validate
import re
from datetime import timedelta, timezone
from pathlib import Path

from dateutil import parser as dateutil_parser

# Mapping for common US timezone abbreviations that dateutil doesn't understand
TZINFOS = {
    "PST": timezone(timedelta(hours=-8)),
    "PDT": timezone(timedelta(hours=-7)),
    "MST": timezone(timedelta(hours=-7)),
    "MDT": timezone(timedelta(hours=-6)),
    "CST": timezone(timedelta(hours=-6)),
    "CDT": timezone(timedelta(hours=-5)),
    "EST": timezone(timedelta(hours=-5)),
    "EDT": timezone(timedelta(hours=-4)),
}
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
from app.watches.models import Watch

load_models()

INPUTS_DIR = Path(__file__).parent / "inputs"
PLUGIN_KEY = "ryn.cx-YouTube"

WATCH_ENTRY_RE = re.compile(
    r'Watched\s*<a href="[^"]*watch\?v=([a-zA-Z0-9_-]+)">[^<]*</a>'
    r"<br>.*?<br>"
    r"([A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2}\s*[AP]M\s*\w+)"
    r"<br>",
    re.DOTALL,
)


def load_watch_history() -> list[tuple[str, str]]:
    """Load all watch history entries from the HTML file.

    Returns:
        List of (video_id, date_string) tuples.
    """
    entries: list[tuple[str, str]] = []
    for html_file in sorted(INPUTS_DIR.glob("*.html")):
        content = html_file.read_text(encoding="utf-8")
        entries.extend(WATCH_ENTRY_RE.findall(content))
    return entries


def import_watches(session: Session, user: User) -> None:
    plugin = session.get(Plugin, PLUGIN_KEY)
    if not plugin:
        logger.warning(f"Plugin '{PLUGIN_KEY}' not found in database")
        return

    # Load all YouTube episodes keyed by their video ID
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

    # Load episode IDs that already have any watch record for this user
    existing_watched_episodes: set[str] = set()
    watch_statement = select(Watch.episode_id).where(
        Watch.user_id == user.id,
    )
    for episode_id in session.exec(watch_statement):
        existing_watched_episodes.add(str(episode_id))

    entries = load_watch_history()
    added = 0
    skipped_not_found = 0
    skipped_already_watched = 0

    for video_id, date_string in entries:
        episode = episodes_by_key.get(video_id)
        if not episode:
            skipped_not_found += 1
            continue

        if str(episode.id) in existing_watched_episodes:
            skipped_already_watched += 1
            continue

        watch_date = dateutil_parser.parse(date_string, tzinfos=TZINFOS)
        episode_watch = Watch(
            user_id=user.id,
            episode_id=episode.id,
            watch_date=watch_date,
            verified=False,
        )
        session.add(episode_watch)
        existing_watched_episodes.add(str(episode.id))
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
