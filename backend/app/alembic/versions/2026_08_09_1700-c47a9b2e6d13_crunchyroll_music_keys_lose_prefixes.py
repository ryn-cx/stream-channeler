"""drop the prefixes from Crunchyroll's music keys

Crunchyroll issues an id under a prefix that already says what it names, so the
`artist/`, `concert/` and `musicvideo/` a key used to be built with said nothing
the id did not. The stored keys are rewritten to the ids themselves, along with
the two identifiers that were built out of a key.

A season has no id of its own, so its key becomes the listing it stands for and
the artist it belongs to is left to the show, which is the only thing that ever
had to say it.

An episode identifier is left as it is: it was always built from the id rather
than from the key, so a watch still names what it watched.

Revision ID: c47a9b2e6d13
Revises: b8e1c7a204df
Create Date: 2026-08-09 17:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c47a9b2e6d13"
down_revision = "b8e1c7a204df"
branch_labels = None
depends_on = None

def upgrade():
    op.execute(
        """
        UPDATE show
        SET key = substring(key from 8),
            show_identifier = replace(
                show_identifier, 'Crunchyroll artist/', 'Crunchyroll '
            )
        WHERE key LIKE 'artist/%'
        """,
    )
    op.execute(
        """
        UPDATE season
        SET key = split_part(key, '/', 3),
            season_identifier = 'Crunchyroll ' || split_part(key, '/', 3)
        WHERE key LIKE 'artist/%/%'
        """,
    )
    op.execute(
        """
        UPDATE episode
        SET key = substring(key from position('/' in key) + 1)
        WHERE key LIKE 'concert/%' OR key LIKE 'musicvideo/%'
        """,
    )
    op.execute(
        """
        UPDATE channelshow
        SET show_identifier = replace(
            show_identifier, 'Crunchyroll artist/', 'Crunchyroll '
        )
        WHERE show_identifier LIKE 'Crunchyroll artist/%'
        """,
    )
    op.execute(
        """
        UPDATE channelseasonfilter
        SET season_identifier =
            'Crunchyroll ' || split_part(season_identifier, '/', 3)
        WHERE season_identifier LIKE 'Crunchyroll artist/%/%'
        """,
    )


def downgrade():
    op.execute(
        """
        UPDATE show
        SET key = 'artist/' || key,
            show_identifier = replace(
                show_identifier, 'Crunchyroll MA', 'Crunchyroll artist/MA'
            )
        WHERE key LIKE 'MA%'
        """,
    )
    op.execute(
        """
        UPDATE season
        SET key = 'artist/' || show.key || '/' || season.key,
            season_identifier =
                'Crunchyroll artist/' || show.key || '/' || season.key
        FROM show
        WHERE season.show_id = show.id
          AND season.key IN ('concert', 'musicvideo')
        """,
    )
    op.execute(
        """
        UPDATE episode
        SET key = 'musicvideo/' || key
        WHERE key LIKE 'MV%'
        """,
    )
    op.execute(
        """
        UPDATE episode
        SET key = 'concert/' || key
        WHERE key LIKE 'MC%'
        """,
    )
    op.execute(
        """
        UPDATE channelshow
        SET show_identifier = replace(
            show_identifier, 'Crunchyroll MA', 'Crunchyroll artist/MA'
        )
        WHERE show_identifier LIKE 'Crunchyroll MA%'
        """,
    )
    op.execute(
        """
        UPDATE channelseasonfilter AS season_filter
        SET season_identifier =
            'Crunchyroll artist/' || show.key || '/' || season_filter.season_identifier
        FROM channelshow
        JOIN show ON show.show_identifier = channelshow.show_identifier
        WHERE season_filter.channel_show_id = channelshow.id
          AND season_filter.season_identifier IN ('Crunchyroll concert',
                                           'Crunchyroll musicvideo')
        """,
    )
