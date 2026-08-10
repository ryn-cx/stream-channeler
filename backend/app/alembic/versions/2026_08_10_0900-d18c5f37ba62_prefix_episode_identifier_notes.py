"""say whether an episode's note was written by hand or by an import

A note now leads with which of the two wrote it. The stored notes are rewritten
so that the ones a `User` settled still read as theirs: `MANUAL_NOTES` is what
`_is_settled_by_hand` reads to know an import may not guess over a decision, and
a note left in the old wording would no longer be found in it.

Revision ID: d18c5f37ba62
Revises: c47a9b2e6d13
Create Date: 2026-08-10 09:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d18c5f37ba62"
down_revision = "c47a9b2e6d13"
branch_labels = None
depends_on = None

RENAMED_NOTES = (
    ("Name and number match", "Automatic: Name and number match"),
    ("Description match", "Automatic: Description match"),
    ("Named the same", "Automatic: Named the same"),
    (
        "Named the same in another language",
        "Automatic: Named the same in another language",
    ),
    ("One name contains the other", "Automatic: One name contains the other"),
    (
        "One name contains the other in another language",
        "Automatic: One name contains the other in another language",
    ),
    (
        "Numbered the same, with no name to go on",
        "Automatic: Numbered the same, with no name to go on",
    ),
    (
        "Numbered the same, in a season of the same length",
        "Automatic: Numbered the same, in a season of the same length",
    ),
    (
        "Closest name of the title, and the number agrees",
        "Automatic: Closest name of the title, and the number agrees",
    ),
    ("Manually confirmed", "Manual: Confirmation"),
    ("Manually selected", "Manual: Selection"),
    ("No match found", "Manual: No match found"),
)


def _rewrite(renames: tuple[tuple[str, str], ...]) -> None:
    """Point every note written one way at the way it is written now."""
    values = ", ".join(
        f"('{old}', '{new}')" for old, new in renames
    )
    op.execute(
        f"""
        UPDATE episode
        SET episode_identifier_note = renamed.new_note
        FROM (VALUES {values}) AS renamed(old_note, new_note)
        WHERE episode.episode_identifier_note = renamed.old_note
        """,  # noqa: S608 - Built from the tuple above, never from stored data.
    )


def upgrade():
    _rewrite(RENAMED_NOTES)


def downgrade():
    _rewrite(tuple((new, old) for old, new in RENAMED_NOTES))
