# TODO: Validate


"""Which canonical show a show is linked to, and the settling of it."""

from sqlmodel import Session

from app.canonical_media.metadata import canonical_show_of
from app.issue_reports.service.listing import list_show_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.shows.models import Show
from app.shows.schemas import (
    ShowInformationOutput,
    ShowInformationSide,
    ShowPublic,
    ShowUpdate,
)
from app.shows.service.extra import update_show_extra
from app.sources.schemas import SourceListPublic
from app.users.models import User


# TODO: Validate
def _show_output(show: Show) -> ShowPublic:
    """Return a `Show` as the website that holds it stored it."""
    return ShowPublic.model_validate(show)


# TODO: Validate
def _information_side(label: str, show: Show) -> ShowInformationSide:
    return ShowInformationSide(
        label=label,
        show=ShowPublic.model_validate(show),
        source=SourceListPublic.model_validate(show.source),
    )


# TODO: Validate
def show_information(
    session: Session,
    show: Show,
    current_user: User | None,
) -> ShowInformationOutput:
    """Return what the website and TMDB each say about a `Show`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    source = show.source

    counterpart = canonical_show_of(session, show)
    tmdb: ShowInformationSide | None = None
    if counterpart:
        tmdb = _information_side(TMDB_PLUGIN_KEY, counterpart)

    return ShowInformationOutput(
        editable=current_user is not None and current_user.is_superuser,
        issue_reports=list_show_issue_reports(session, show.id),
        source=_information_side(
            source.name or source.plugin.key,
            show,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
def update_show_record(
    session: Session,
    show: Show,
    show_input: ShowUpdate,
) -> ShowPublic:
    """Write an update to a `Show`.

    Which canonical show this stands for is not something an update writes: it is
    linker's to work out during an import, or a `User`'s to settle through the
    TMDB matching screens, so there is nothing to repoint here.

    `extra` goes through its own service rather than being written with the rest, since
    what a TMDB row keeps there is the episode order the title is read in and changing
    that means reading the title again and matching every non-canonical row of it
    afresh.
    """
    # Before the rest of the update, because what it does depends on the order
    # the title is read in now and the general write would already have replaced
    # it. The same value going down twice writes nothing the second time.
    if "extra" in show_input.model_fields_set:
        update_show_extra(session, show, show_input.extra)
    return _show_output(show_input.update(session, show))
