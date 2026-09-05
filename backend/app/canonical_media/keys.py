# TODO: Validate
"""What a canonical row's `key` says, and how to read it back.

A canonical row is named by one namespaced string rather than by columns of its
own. "YouTube dQw4w9WgXcQ" is a video only YouTube knows about; "TMDB tv 1399" is
a record TMDB holds. The first word says who issued the key, so no two sources
can collide on one.
"""

from sqlalchemy import ColumnElement, func


# TODO: Validate
def watch_identifier(plugin_key: str, key: str) -> str:
    """Return what a `Watch` of the episode `plugin_key` keyed as `key` is of.

    A plugin's own key names the media itself rather than one row for it — a
    YouTube episode is keyed by its video id, which is the same id wherever that
    video turns up — so namespacing it by the plugin is enough to say that two
    rows are of the same media.
    """
    return f"{plugin_key} {key}"


# TODO: Validate
def key_issuer(key_column: ColumnElement[str]) -> ColumnElement[str]:
    """Return who issued the record `key_column` names."""
    return func.split_part(key_column, " ", 1)


# TODO: Validate
def same_issuer_clause(
    first: ColumnElement[str],
    second: ColumnElement[str],
) -> ColumnElement[bool]:
    """Return the filter matching two keys that were issued by the same source.

    A canonical show's own catalogue is the run of records whoever issued the
    show issued, so a row a website minted under a show TMDB issued is a record
    of the website's rather than one of the show's own. A website carries an
    episode the show has no record of - an extra it filed under the season, a
    film it sells as part of the series - and a canonical row is minted for it
    so the row has something to hang off, but the show it was filed under
    still does not hold it.
    """
    return key_issuer(first) == key_issuer(second)
