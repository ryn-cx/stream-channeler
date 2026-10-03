// TODO: Validate
import { useMutationState, useQueryClient } from "@tanstack/react-query"
import { useMemo } from "react"

/** Where the table of episodes waiting on a TMDB link is held in the cache. */
export const TMDB_MATCHES_QUERY_KEY = ["admin-tmdb-matches"]

export const SETTLE_TMDB_MATCH_MUTATION_KEY = ["settle-tmdb-match"]

export interface SettleTmdbMatchVariables {
  episodeIds: string[]
}

// TODO: Validate
export function useSettlingTmdbMatchIds(dataUpdatedAt: number) {
  const settling = useMutationState({
    filters: {
      mutationKey: SETTLE_TMDB_MATCH_MUTATION_KEY,
      predicate: (mutation) => mutation.state.status !== "error",
    },
    select: (mutation) => ({
      episodeIds:
        (mutation.state.variables as SettleTmdbMatchVariables | undefined)
          ?.episodeIds ?? [],
      submittedAt: mutation.state.submittedAt,
      isPending: mutation.state.status === "pending",
    }),
  })
  const settlingKey = settling
    .filter((settle) => settle.isPending || settle.submittedAt > dataUpdatedAt)
    .flatMap((settle) => settle.episodeIds)
    .sort()
    .join(",")
  return useMemo(
    () => new Set(settlingKey === "" ? [] : settlingKey.split(",")),
    [settlingKey],
  )
}

// TODO: Validate
export function useRereadTmdbMatches() {
  const queryClient = useQueryClient()
  return async () => {
    await queryClient.cancelQueries({ queryKey: TMDB_MATCHES_QUERY_KEY })
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: TMDB_MATCHES_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: ["admin-tmdb-choices"] }),
    ])
  }
}
