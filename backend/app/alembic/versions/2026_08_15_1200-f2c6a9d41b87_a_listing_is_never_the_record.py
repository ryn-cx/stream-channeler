"""a listing is never the record

A title nothing catalogues had no record of its own, so the first listing of it
written was raised to one and the rest were made to stand for that listing. Which
listing got raised came down to nothing better than which was written first, and
the one that was is watchable and stood for at once, which is the shape the levels
are meant never to take.

Every such listing is put back down. The record it was standing in for is written
as a row of its own, named by the plugin's key for the title the way `record_key`
names it, every listing that stood for the raised listing is moved onto it, and the
raised listing is made to stand for it alongside the others.

A canonical listing nothing stands for is left alone: it is settled the next time
it is written, which is what the raised ones could never be.

Revision ID: f2c6a9d41b87
Revises: e9d4b7c25f13
Create Date: 2026-08-15 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f2c6a9d41b87"
down_revision = "e9d4b7c25f13"
branch_labels = None
depends_on = None

# The listings that were raised, and the key the record standing in for each of
# them belongs under. Held rather than asked for again, because the first thing
# the move does is take away what says a listing was raised.
_PROMOTED = """
CREATE TEMP TABLE promoted_listing ON COMMIT DROP AS
SELECT show.id AS listing_id,
       show.source_id AS source_id,
       plugin.key || ' ' || show.key AS record_key
FROM show
JOIN source ON source.id = show.source_id
JOIN plugin ON plugin.id = source.plugin_id
WHERE show.is_canonical
  AND show.key NOT LIKE 'TMDB %'
  AND EXISTS (
      SELECT 1 FROM showcanonicalshow
      WHERE showcanonicalshow.canonical_show_id = show.id
  )
"""

# The record itself, saying what the raised listing said about the title. It hangs
# off the same source, which is the one the title was read from.
_MINT_RECORDS = """
INSERT INTO show (id, created_at, modified_at, key, name, media_type, description,
                  url, image_url, year, canonical_show_locked, is_canonical,
                  source_id)
SELECT gen_random_uuid(), now(), now(), promoted_listing.record_key, show.name,
       show.media_type, show.description, show.url, show.image_url, show.year,
       FALSE, TRUE, show.source_id
FROM promoted_listing
JOIN show ON show.id = promoted_listing.listing_id
ON CONFLICT (source_id, key) DO NOTHING
"""

_PAIRS = """
CREATE TEMP TABLE promoted_pair ON COMMIT DROP AS
SELECT promoted_listing.listing_id, record.id AS record_id
FROM promoted_listing
JOIN show AS record
  ON record.source_id = promoted_listing.source_id
 AND record.key = promoted_listing.record_key
"""

_REPOINT_LINKS = """
UPDATE showcanonicalshow
SET canonical_show_id = promoted_pair.record_id
FROM promoted_pair
WHERE showcanonicalshow.canonical_show_id = promoted_pair.listing_id
"""

_LINK_PROMOTED = """
INSERT INTO showcanonicalshow (id, created_at, modified_at, show_id,
                               canonical_show_id)
SELECT gen_random_uuid(), now(), now(), promoted_pair.listing_id,
       promoted_pair.record_id
FROM promoted_pair
ON CONFLICT (show_id, canonical_show_id) DO NOTHING
"""

_DEMOTE = """
UPDATE show
SET is_canonical = FALSE
FROM promoted_pair
WHERE show.id = promoted_pair.listing_id
"""

# The rule the move is for: no row is stood for by something and standing for
# something else.
_DEPTH_CHECK = """
DO $$
DECLARE
    wrong bigint;
BEGIN
    SELECT count(*) INTO wrong
    FROM show
    WHERE EXISTS (
              SELECT 1 FROM showcanonicalshow
              WHERE showcanonicalshow.canonical_show_id = show.id
          )
      AND EXISTS (
              SELECT 1 FROM showcanonicalshow
              WHERE showcanonicalshow.show_id = show.id
          );
    IF wrong > 0 THEN
        RAISE EXCEPTION '% show rows are a listing and a record at once', wrong;
    END IF;
END $$;
"""

# Going back, the record hands what it holds to the oldest listing of it, which
# is as near as anything comes to the one that would have been raised first.
_MINTED = """
CREATE TEMP TABLE minted_record ON COMMIT DROP AS
SELECT record.id AS record_id,
       (
           SELECT link.show_id
           FROM showcanonicalshow AS link
           JOIN show AS listing ON listing.id = link.show_id
           WHERE link.canonical_show_id = record.id
           ORDER BY listing.created_at, listing.id
           LIMIT 1
       ) AS listing_id
FROM show AS record
JOIN source ON source.id = record.source_id
JOIN plugin ON plugin.id = source.plugin_id
WHERE record.is_canonical
  AND record.key LIKE plugin.key || ' %'
"""

_DROP_UNSTOOD = """
DELETE FROM minted_record WHERE listing_id IS NULL
"""

_UNLINK_PROMOTED = """
DELETE FROM showcanonicalshow
USING minted_record
WHERE showcanonicalshow.show_id = minted_record.listing_id
  AND showcanonicalshow.canonical_show_id = minted_record.record_id
"""

_REPOINT_BACK = """
UPDATE showcanonicalshow
SET canonical_show_id = minted_record.listing_id
FROM minted_record
WHERE showcanonicalshow.canonical_show_id = minted_record.record_id
"""

_PROMOTE_BACK = """
UPDATE show
SET is_canonical = TRUE
FROM minted_record
WHERE show.id = minted_record.listing_id
"""

_DROP_RECORDS = """
DELETE FROM show
USING minted_record
WHERE show.id = minted_record.record_id
"""


def upgrade() -> None:
    op.execute(_PROMOTED)
    op.execute(_MINT_RECORDS)
    op.execute(_PAIRS)
    op.execute(_REPOINT_LINKS)
    op.execute(_LINK_PROMOTED)
    op.execute(_DEMOTE)
    op.execute(_DEPTH_CHECK)


def downgrade() -> None:
    op.execute(_MINTED)
    op.execute(_DROP_UNSTOOD)
    op.execute(_UNLINK_PROMOTED)
    op.execute(_REPOINT_BACK)
    op.execute(_PROMOTE_BACK)
    op.execute(_DROP_RECORDS)
