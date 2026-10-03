# TODO: Validate


"""Which canonical title a title is linked to, and the settling of it."""

from app.titles.service.linking.manual_linking import (
    mark_title_absent_from_tmdb,
    old_import_linked_title_from_url,
    old_link_title_to_tmdb_title,
    old_link_title_to_tmdb_title_from_url,
    old_make_title_unlinked,
    old_relink_title,
    old_unlink_title_from_tmdb_title,
    tmdb_title_from_url,
    unlink_titles_from_tmdb_title,
    unmark_title_absent_from_tmdb,
)
from app.titles.service.linking.title_linker import (
    TitleLinker,
    link_new_title_to_tmdb,
    link_title,
)
from app.titles.service.linking.tmdb_links import (
    link_unlinked_title_to_tmdb,
    old_link_title_to_tmdb,
)

__all__ = [
    "TitleLinker",
    "link_new_title_to_tmdb",
    "link_title",
    "link_unlinked_title_to_tmdb",
    "mark_title_absent_from_tmdb",
    "old_import_linked_title_from_url",
    "old_link_title_to_tmdb",
    "old_link_title_to_tmdb_title",
    "old_link_title_to_tmdb_title_from_url",
    "old_make_title_unlinked",
    "old_relink_title",
    "old_unlink_title_from_tmdb_title",
    "tmdb_title_from_url",
    "unlink_titles_from_tmdb_title",
    "unmark_title_absent_from_tmdb",
]
