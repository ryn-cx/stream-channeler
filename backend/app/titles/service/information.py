# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

from sqlmodel import Session

from app.canonical_media.metadata import canonical_title_of
from app.issue_reports.service.listing import list_title_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.sources.schemas import SourceListPublic
from app.titles.models import Title
from app.titles.schemas import (
    TitleInformationOutput,
    TitleInformationSide,
    TitlePublic,
    TitleUpdate,
)
from app.titles.service.extra import update_title_extra
from app.users.models import User


# TODO: Validate
def _title_output(title: Title) -> TitlePublic:
    """Return a `Title` as the website that holds it stored it."""
    return TitlePublic.model_validate(title)


# TODO: Validate
def _information_side(label: str, title: Title) -> TitleInformationSide:
    return TitleInformationSide(
        label=label,
        title=TitlePublic.model_validate(title),
        source=SourceListPublic.model_validate(title.source),
    )


# TODO: Validate
def title_information(
    session: Session,
    title: Title,
    current_user: User | None,
) -> TitleInformationOutput:
    """Return what the website and TMDB each say about a `Title`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    source = title.source

    counterpart = canonical_title_of(session, title)
    tmdb: TitleInformationSide | None = None
    if counterpart:
        tmdb = _information_side(TMDB_PLUGIN_KEY, counterpart)

    return TitleInformationOutput(
        editable=current_user is not None and current_user.is_superuser,
        issue_reports=list_title_issue_reports(session, title.id),
        source=_information_side(
            source.name or source.plugin.key,
            title,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
def update_title_record(
    session: Session,
    title: Title,
    title_input: TitleUpdate,
) -> TitlePublic:
    """Write an update to a `Title`.

    Which canonical title this stands for is not something an update writes: it is
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
    if "extra" in title_input.model_fields_set:
        update_title_extra(session, title, title_input.extra)
    return _title_output(title_input.update(session, title))
