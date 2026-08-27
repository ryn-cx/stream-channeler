// TODO: Validate
import { type QueryKey, useQueryClient } from "@tanstack/react-query"

import type { UnmatchedEpisodesPublic } from "@/client"

/** Where the table of episodes waiting on a TMDB link is held in the cache. */
export const TMDB_MATCHES_QUERY_KEY = ["admin-tmdb-matches"]

/** Every page of the table as it read before a row was settled. */
export type SettledMatches = Array<
  [QueryKey, UnmatchedEpisodesPublic | undefined]
>

// TODO: Validate
function withoutEpisode(
  page: UnmatchedEpisodesPublic | undefined,
  episodeId: string,
): UnmatchedEpisodesPublic | undefined {
  if (!page) return page
  const data = page.data.filter((row) => row.episode.id !== episodeId)
  if (data.length === page.data.length) return page
  const settled = page.data.length - data.length
  return {
    ...page,
    data,
    total_count: page.total_count - settled,
    filtered_count: page.filtered_count - settled,
  }
}

// TODO: Validate
/**
 * Take a row out of the table the moment it is settled, and put it back if it
 * turns out not to be.
 *
 * Settling a row is worked through a page at a time, and waiting on the round
 * trip leaves the row that was just dealt with sitting there under the pointer.
 * The row is dropped from every page held in the cache instead, and the pages
 * are read again once the server has answered either way, so a count the drop
 * only guessed at settles to what the server says.
 *
 * The pages are keyed by the paging and sorting they were read with, so every
 * one of them is written to rather than the one on screen: the same episode is
 * on the page behind whichever is showing once the table pages backwards.
 *
 * Every button that settles a row uses this, including the picker's, which is
 * shown from an episode's own page as well. There it finds no page holding the
 * episode and does nothing, which is the whole of what it should do.
 */
export function useSettleTmdbMatch() {
  const queryClient = useQueryClient()

  // TODO: Validate
  const settle = async (episodeId: string): Promise<SettledMatches> => {
    await queryClient.cancelQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })
    const previous = queryClient.getQueriesData<UnmatchedEpisodesPublic>({
      queryKey: TMDB_MATCHES_QUERY_KEY,
    })
    queryClient.setQueriesData<UnmatchedEpisodesPublic>(
      { queryKey: TMDB_MATCHES_QUERY_KEY },
      (page) => withoutEpisode(page, episodeId),
    )
    return previous
  }

  // TODO: Validate
  const restore = (previous: SettledMatches | undefined) => {
    for (const [queryKey, page] of previous ?? []) {
      queryClient.setQueryData(queryKey, page)
    }
  }

  // TODO: Validate
  const reread = () => {
    queryClient.invalidateQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })
    queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] })
  }

  return { settle, restore, reread }
}
