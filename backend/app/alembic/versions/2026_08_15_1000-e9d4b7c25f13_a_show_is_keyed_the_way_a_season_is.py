"""a show is keyed the way a season is

Revision ID: e9d4b7c25f13
Revises: d8b3c15f7a26
Create Date: 2026-08-15 10:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e9d4b7c25f13"
down_revision = "d8b3c15f7a26"
branch_labels = None
depends_on = None

# What points at a show, all of it at `id`. A foreign key cannot outlive the
# constraint it rests on, so each is dropped before the primary key moves and put
# back afterwards against the unique constraint `id` keeps.
_SHOW_REFERENCES = (
    (
        "channelepisodesourcefilter",
        "channelepisodesourcefilter_show_id_fkey",
        "show_id",
    ),
    ("channelshow", "channelshow_canonical_show_id_fkey", "canonical_show_id"),
    ("channelsourcefilter", "channelsourcefilter_show_id_fkey", "show_id"),
    ("season", "season_show_id_fkey", "show_id"),
    (
        "showcanonicalshow",
        "showcanonicalshow_canonical_show_id_fkey",
        "canonical_show_id",
    ),
    ("showcanonicalshow", "showcanonicalshow_show_id_fkey", "show_id"),
    ("showissuereport", "showissuereport_show_id_fkey", "show_id"),
)


def upgrade() -> None:
    for table, name, _column in _SHOW_REFERENCES:
        op.drop_constraint(name, table, type_="foreignkey")

    # The pair was already unique over every row and neither column allows
    # nothing, so it is a primary key as it stands and no row has to be checked.
    op.drop_constraint("Show-source_id-key-key", "show", type_="unique")
    op.execute("ALTER TABLE show DROP CONSTRAINT show_pkey")
    op.execute("ALTER TABLE show ADD CONSTRAINT show_pkey PRIMARY KEY (source_id, key)")
    op.create_unique_constraint("show_id_key", "show", ["id"])

    for table, name, column in _SHOW_REFERENCES:
        op.create_foreign_key(
            name,
            table,
            "show",
            [column],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table, name, _column in _SHOW_REFERENCES:
        op.drop_constraint(name, table, type_="foreignkey")

    op.execute("ALTER TABLE show DROP CONSTRAINT show_pkey")
    op.execute("ALTER TABLE show ADD CONSTRAINT show_pkey PRIMARY KEY (id)")
    op.drop_constraint("show_id_key", "show", type_="unique")
    op.create_unique_constraint(
        "Show-source_id-key-key",
        "show",
        ["source_id", "key"],
    )

    for table, name, column in _SHOW_REFERENCES:
        op.create_foreign_key(
            name,
            table,
            "show",
            [column],
            ["id"],
            ondelete="CASCADE",
        )
