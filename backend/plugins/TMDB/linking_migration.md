<!-- TODO: Validate -->
# TMDB linking and reconciling, once per listing

Applies to every plugin still in the tree: Crunchyroll, JustWatch, NHKWorld and
YouTube. Any plugin brought back from git history needs the same edits before it
will run, since the helpers it used to call have changed shape.

## TMDB manages its own files

A plugin used to list TMDB's files among its own, so a website's copy was held
back waiting on a TMDB download and a TMDB refresh moved the copy's
`data_timestamp`. That is gone: `_show_files` / `_season_files` /
`_episode_files` now return only the plugin's own files, and `TMDBMixin` no
longer overrides them. `_append_tmdb_*_file`, `_tmdb_*_file`,
`_download_files_the_tmdb_lookup_reads` and the `_listing_files_only` recursion
guard that existed to support them are all deleted.

TMDB's files are fetched by the lookups that read them, each already calling
`download_if_outdated`, so `_link_tmdb` pulls whatever the matching needs when it
runs. `_movie_detail` was the one lookup that only parsed without downloading —
it was relying on the plugin having listed the file — so it downloads now like
its siblings.

Two knock-on effects worth knowing:

- A show's `data_timestamp` and `update_at` are computed off its files, so they
  no longer move when TMDB updates. That is the point, but it changes when
  records come up for update.
- `_get_season_number` has no caller left — the TMDB file helpers were the only
  ones — and `_get_episode_number` is now used only by YouTube. Both are still
  declared on `TMDBMixin` and implemented in all four plugins. Worth deciding
  whether to delete them or move `_get_episode_number` to YouTube.

## What changed outside the plugins

`_upsert_show_object` / `_upsert_season_object` / `_upsert_episode_object` live on
`BasePlugin` rather than `TMDBMixin`, and no longer link anything. Each is an
upsert against the record's files, plus carrying the stored canonical id over:
locked always wins, unlocked is kept only where the new record names nothing
better. The episode's note travels with its id.

`TMDBMixin` holds:

`TMDBLinker` (`plugins/TMDB/link.py`) is the whole of it, and it is neither a
plugin nor a mixin. No plugin inherits anything TMDB; a plugin builds a linker
for its session and makes one call:

```python
TMDBLinker(session).link(
    show,
    plugin_key,
    media_type,          # None for something TMDB does not catalogue
    name=...,            # searched for only when nothing already knows the title
    year=...,
    canonical_show=...,  # a title the caller already holds
)
```

That one call works out which title the listing is of, links the show, its
seasons and its episodes, downloads the TMDB files the matching reads, unshares
and reconciles. Which title it is comes from `canonical_show` when a caller
holds one, else from what the listing or another copy of it already resolved,
else by searching TMDB under `name` and `year` — a request, so it is the last
thing tried rather than the first.

The TMDB plugin is what the linker downloads and upserts through, held as
`linker.tmdb`, so nothing about fetching or storing TMDB's data lives in the
plugin being linked. The `TMDB` plugin does not inherit the linking either —
`LinkMixin` is gone from its bases. `TMDBMixin` is deleted; each plugin's
`FileMixin` extends `BasePlugin` directly.

`unshare_canonical_episodes` moved out of `BasePlugin` to
`plugins/TMDB/unshare.py`, since linking, unsharing and reconciling are now one
operation the linker owns.

`media_type` is passed in rather than worked out here. The plugin's own branch
already decided whether it was upserting a film or a series, so it says which,
and `None` says the listing is of something TMDB does not catalogue at all — a
YouTube channel, a Crunchyroll artist. That replaced the `_has_tmdb_entry` hook,
which is deleted along with YouTube's `has_tmdb_entry`.

`BasePlugin._preload_and_upsert_show` and `_import_show` no longer unshare and
reconcile after calling `upsert_show`. Every plugin's `upsert_show` ends on that
pair itself, so the paths that never went through those two — JustWatch importing
a title for one source, YouTube importing a show for one playlist — get it too.
YouTube's `_upsert_and_reconcile_show`, which existed only to fill that gap, is
gone.

## What a plugin's `upsert_show` owes

1. **No media type argument** on `_upsert_*_object` calls. The media type comes
   from `tmdb_media_type(show_key)` inside `_link_tmdb`, so check the plugin's
   `tmdb_media_type` discriminates movie from tv the way the branch that used to
   pass `MediaType.movie` did.
2. **No last-episode-number argument** on `_upsert_episode_object`, and nothing
   computing one. Check the value `_link_tmdb` computes off the stored
   `episode_number`s matches what the plugin used to pass — a plugin numbering
   its episodes differently from what it stores is the case to watch for.
3. **End on `TMDBLinker(self.session).link(...)`**, after the soft-deletes so
   removed records are left alone. Every listing reaches it, including one TMDB
   holds nothing for — pass `None` as the media type rather than skipping the
   call, since it still has to reconcile.
4. A plugin whose `upsert_show` returns straight out of each branch needs
   restructuring to assign then finish.
5. **Take `canonical_show` as a keyword argument** and hand it to `_link_tmdb`.
   It is the title a caller named the listing as a copy of, carried down from
   `import_url` as an argument rather than held on the instance, so nothing has
   to survive between calls for it to be read.

## Behaviour to be aware of when validating

- Linking now runs over every active season and episode on each `upsert_show`,
  not only the records the import decided were outdated. An episode's match
  depends on what the rest of the listing turned out to be, which is the reason
  for the move, but it means more TMDB lookups per run and a record left alone as
  up to date is re-matched.
- `Show.upsert` and `Episode.upsert` protect a `User`'s locked link by excluding
  it from the merge. Linking after the upsert bypasses that, so `_link_tmdb`
  skips `canonical_show_locked` shows and `canonical_episode_locked` episodes
  itself. Anything else added to those protected keys has to be repeated there.
- JustWatch's `upsert_show` returns early when a source has stopped offering a
  title, soft deleting the show. That path now reconciles nothing, where the
  reconcile in `_import_show` used to catch it. A soft deleted show has no rows
  to work out, but it is the one place the behaviour changed rather than moved.
- `canonical_show_id`, `canonical_season_id` and `canonical_episode_id` are
  declared `Field(default=None, ...)`. The column stays `NOT NULL` — sqlmodel
  takes nullability off the annotation, not the default — and the default only
  stops the constructor demanding an id the caller cannot know until the flush.
