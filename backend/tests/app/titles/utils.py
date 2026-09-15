# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.users.models import User
from tests.app.helpers.utils import build_random_model
from tests.app.sources.utils import create_random_source
from tests.app.users.utils import CreatedUser


# TODO: Validate
def create_random_title(
    session: Session,
    parent: Source | Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Title:
    if not isinstance(parent, Source):
        parent = create_random_source(session, parent)
    # A title no other record exists of is the record, so it stands for itself and
    # its own id is the canonical title id everything else names it by. Building
    # the linked pair instead is what a test that is about linking does for itself.
    kwargs.setdefault("is_linked", False)
    title = build_random_model(Title, source_id=parent.id, deleted_at=None, **kwargs)
    session.add(title)
    session.flush()  # Allows title.source and title.seasons to be accessed.
    return title
