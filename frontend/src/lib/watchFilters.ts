// TODO: Validate
/**
 * The watch state of an episode, mirroring how the backend groups them:
 * "watched" is a verified watch, "partiallyWatched" is a watch that has not been
 * verified, and "unwatched" is no watch at all.
 */
export type WatchState = "watched" | "partiallyWatched" | "unwatched"

/** The channel filters that hide episodes by their watch state. */
export interface WatchFilters {
  hideWatched?: boolean
  hideUnwatched?: boolean
  hidePartiallyWatched?: boolean
}

/**
 * Whether the active filters exclude an episode in `state`.
 *
 * Used after a watch is created, verified or deleted to decide whether the
 * episode should drop out of the list, so an optimistic update matches what the
 * next fetch would return.
 */
export function isHiddenByWatchFilters(
  state: WatchState,
  filters: WatchFilters | undefined,
): boolean {
  if (!filters) return false
  if (state === "watched") return filters.hideWatched === true
  if (state === "partiallyWatched") return filters.hidePartiallyWatched === true
  return filters.hideUnwatched === true
}
