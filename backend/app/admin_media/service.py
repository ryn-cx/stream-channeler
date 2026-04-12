from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


def force_update(
    session: Session,
    record: Episode | Season | Show | Source | Plugin,
) -> Message:
    """Set update_at to now, commit the change, and return a Message."""
    record.update_at = tz_datetime.now()
    session.commit()
    return Message(message=f"{record} \nSet to update")
