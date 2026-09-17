# TODO: Validate
"""An Amazon source is named for its channel rather than for its benefit id."""

from alembic import op

revision = "a8c4d1e6b972"
down_revision = "f3b19d07ca44"
branch_labels = None
depends_on = None


_CHANNEL_NAMES = """
VALUES
    ('acorn', 'Acorn TV'),
    ('aetncrimecentral', 'A&E Crime Central'),
    ('amcplus', 'AMC+'),
    ('amebatv', 'Ameba'),
    ('aspireTVus', 'aspireTV+'),
    ('bbcselect', 'BBC Select'),
    ('bestofbritish', 'Best of British Television'),
    ('bestwesternsever', 'Best Westerns Ever'),
    ('bfiplayer', 'BFI Player Classics'),
    ('britbox', 'BritBox'),
    ('britboxpremierus', 'BritBox'),
    ('broadwayhd', 'BroadwayHD'),
    ('cbsaacf', 'Paramount+'),
    ('cinemax', 'Cinemax'),
    ('cineverseus', 'Cineverse'),
    ('cjus', 'CJ ENM Selects'),
    ('codacollection', 'The Coda Collection'),
    ('cohen', 'Cohen Media Channel'),
    ('contv', 'MIDNIGHT PULP'),
    ('crunchyrollus', 'Crunchyroll'),
    ('curiositystreamstandard', 'Curiosity Stream'),
    ('curiosityuniversityus', 'Curiosity University'),
    ('daringdocs', 'Daring Docs'),
    ('dekkoo', 'Dekkoo'),
    ('discoveryplus', 'discovery+'),
    ('docclub', 'Sundance Now'),
    ('docuramaFilms', 'Docurama'),
    ('dove', 'Dove Channel'),
    ('dox', 'Dox'),
    ('echoboom', 'Echoboom Sports'),
    ('epix', 'MGM+'),
    ('erosnow', 'Eros Now'),
    ('fandor', 'Fandor'),
    ('fearfactory', 'Fear Factory'),
    ('filmbox', 'FilmBox+ Now'),
    ('filmmovementus', 'Film Movement Plus'),
    ('flixlatino', 'FlixLatino'),
    ('france_channel', 'France Channel'),
    ('fullmoon', 'Full Moon'),
    ('fuse', 'Fuse+'),
    ('gaia', 'Gaia'),
    ('hallmark', 'Hallmark+'),
    ('hbomaxus', 'HBO Max'),
    ('heretv', 'Here TV'),
    ('hidiveus', 'HIDIVE'),
    ('historyvault', 'HISTORY Vault'),
    ('hiyah', 'Hi-YAH!'),
    ('hopsterus', 'PlayKids Learning'),
    ('howdyus', 'Howdy'),
    ('indieclub', 'Indie Club'),
    ('indieflix', 'iNDIEFLIX'),
    ('indiepix', 'IndiePix Unlimited'),
    ('insideoutside', 'Inside Outside'),
    ('jedge', 'Doki'),
    ('kidgenius', 'Kartoon Channel'),
    ('kidstream', 'Kidstream'),
    ('kinofilmcollectionus', 'Kino Film Collection'),
    ('lifetimemovieclub', 'Lifetime Movie Club'),
    ('lionsgateplusus', 'Lionsgate+'),
    ('magnoliaselects', 'Magnolia Selects'),
    ('mandn', 'Monsters and Nightmares'),
    ('marqueetvus', 'Marquee TV'),
    ('masterpiece', 'PBS Masterpiece'),
    ('mhzchoice', 'MHz Choice'),
    ('minnokidsus', 'Minno Kids'),
    ('mubi', 'MUBI'),
    ('outside', 'Outside TV Features'),
    ('outtvus', 'OUTtv'),
    ('paramountpremium', 'Paramount+'),
    ('passionflix', 'Passionflix'),
    ('pbo', 'Pinoy Box Office'),
    ('pbsdoc', 'PBS Documentaries'),
    ('pbsliving', 'PBS Living'),
    ('peacockus', 'Peacock Premium Plus'),
    ('pureflixus1', 'Great American Pure Flix'),
    ('qelloconcerts', 'Qello Concerts'),
    ('revry', 'Revry'),
    ('screambox', 'Screambox'),
    ('screenpix', 'ScreenPix'),
    ('sensicalus', 'Sensical'),
    ('shoutfactory', 'Shout! TV'),
    ('shuddertv', 'Shudder'),
    ('shuddertvus', 'Shudder'),
    ('spcoreus', 'Sony Pictures Core'),
    ('starzSub', 'STARZ'),
    ('stingraydjazz', 'Stingray Djazz'),
    ('strandreleasing', 'Strand Releasing'),
    ('tastemade', 'Tastemade'),
    ('theafricachannelus', 'Demand Africa'),
    ('thesurfnetwork', 'The Surf Network'),
    ('tribecashortlist', 'MovieSphere+'),
    ('trueroyalty', 'True Royalty'),
    ('umc', 'ALLBLK'),
    ('upfaithfamily', 'UP Faith & Family'),
    ('vaporvue', 'FUEL TV+'),
    ('vemoxcine', 'Vemox Cine'),
    ('viaplayus', 'Viaplay'),
    ('viewster', 'RetroCrush'),
    ('vixplusus', 'ViX Premium'),
    ('vixus', 'ViX Gratis'),
    ('wag', 'Warriors & Gangsters'),
    ('wonderprojectus', 'Wonder Project'),
    ('xivetv', 'XiveTV Documentaries'),
    ('xltv', 'XLTV'),
    ('yippeetvus', 'Yippee Kids TV')
"""

_COLLECT_RENAMES = f"""
    CREATE TEMPORARY TABLE amazon_rename ON COMMIT DROP AS
    WITH channel_name (benefit_id, channel) AS ({_CHANNEL_NAMES}),
    renamed AS (
        SELECT source.id AS source_id,
               source.plugin_id,
               channel_name.channel || ' on Amazon' AS new_key,
               row_number() OVER (
                   PARTITION BY source.plugin_id, channel_name.channel
                   ORDER BY (source.key = channel_name.channel || ' on Amazon') DESC,
                            source.key
               ) AS position
        FROM source
        JOIN plugin ON plugin.id = source.plugin_id
        JOIN channel_name
          ON source.key = 'Amazon Prime Video:' || channel_name.benefit_id
          OR source.key = channel_name.channel || ' on Amazon'
        WHERE plugin.key = 'Amazon Prime Video'
    )
    SELECT renamed.source_id,
           renamed.new_key,
           first_value(renamed.source_id) OVER (
               PARTITION BY renamed.plugin_id, renamed.new_key
               ORDER BY renamed.position
           ) AS kept_source_id
    FROM renamed
"""

_MOVE_TITLES = """
    UPDATE title
    SET source_id = amazon_rename.kept_source_id
    FROM amazon_rename
    WHERE title.source_id = amazon_rename.source_id
      AND amazon_rename.source_id <> amazon_rename.kept_source_id
      AND NOT EXISTS (
          SELECT 1
          FROM title AS kept_title
          WHERE kept_title.source_id = amazon_rename.kept_source_id
            AND kept_title.key = title.key
      )
"""

_DROP_MERGED_SOURCES = """
    DELETE FROM source
    USING amazon_rename
    WHERE source.id = amazon_rename.source_id
      AND amazon_rename.source_id <> amazon_rename.kept_source_id
"""

_RENAME_CHANNEL_SOURCES = """
    UPDATE source
    SET key = amazon_rename.new_key
    FROM amazon_rename
    WHERE source.id = amazon_rename.source_id
      AND source.key <> amazon_rename.new_key
"""

_RENAME_PURCHASE_SOURCE = """
    UPDATE source
    SET key = 'Purchase on Amazon'
    FROM plugin
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon Prime Video'
      AND source.key = 'Amazon Prime Video:Purchase'
"""

_RESTORE_PURCHASE_SOURCE = """
    UPDATE source
    SET key = 'Amazon Prime Video:Purchase'
    FROM plugin
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon Prime Video'
      AND source.key = 'Purchase on Amazon'
"""

_RESTORE_CHANNEL_SOURCES = f"""
    UPDATE source
    SET key = 'Amazon Prime Video:' || benefit.benefit_id
    FROM plugin,
         (
             SELECT DISTINCT ON (channel) channel, benefit_id
             FROM ({_CHANNEL_NAMES}) AS channel_name (benefit_id, channel)
             ORDER BY channel, benefit_id
         ) AS benefit
    WHERE plugin.id = source.plugin_id
      AND plugin.key = 'Amazon Prime Video'
      AND source.key = benefit.channel || ' on Amazon'
"""


# TODO: Validate
def upgrade() -> None:
    op.execute(_COLLECT_RENAMES)
    op.execute(_MOVE_TITLES)
    op.execute(_DROP_MERGED_SOURCES)
    op.execute(_RENAME_CHANNEL_SOURCES)
    op.execute(_RENAME_PURCHASE_SOURCE)


# TODO: Validate
def downgrade() -> None:
    op.execute(_RESTORE_CHANNEL_SOURCES)
    op.execute(_RESTORE_PURCHASE_SOURCE)
