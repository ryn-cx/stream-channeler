// TODO: Validate
import { useMutationState, useQueryClient } from "@tanstack/react-query"

/** Where the table of episodes waiting on a TMDB link is held in the cache. */
export const TMDB_MATCHES_QUERY_KEY = ["admin-tmdb-matches"]

export const SETTLE_TMDB_MATCH_MUTATION_KEY = ["settle-tmdb-match"]

export interface SettleTmdbMatchVariables {
  episodeIds: string[]
}

// TODO: Validate
export function useSettlingTmdbMatchIds() {
  const settling = useMutationState({
    filters: { mutationKey: SETTLE_TMDB_MATCH_MUTATION_KEY, status: "pending" },
    select: (mutation) =>
      (mutation.state.variables as SettleTmdbMatchVariables).episodeIds,
  })
  return new Set(settling.flat())
}

// TODO: Validate
export function useRereadTmdbMatches() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: TMDB_MATCHES_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] }),
    ])
}
