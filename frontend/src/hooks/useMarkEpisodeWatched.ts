// TODO: Validate
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { WatchesService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

function updateEpisodeInData(oldData: any, episodeId: string, patch: object) {
  if (!oldData) return oldData
  return {
    ...oldData,
    episodes: oldData.episodes.map((ep: any) =>
      ep.id === episodeId ? { ...ep, ...patch } : ep,
    ),
  }
}

export function useMarkWatched(channelId: string | undefined) {
  const { showSuccessToast, showErrorToast, showWarningToast } =
    useCustomToast()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (episodeId: string) =>
      WatchesService.createWatch({
        episodeId,
        requestBody: {
          watch_date: new Date().toISOString(),
          verified: false,
        },
      }),
    // When mutate is called:
    onMutate: async (episodeId) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({
        queryKey: ["episodes", channelId],
      })

      // Snapshot all matching queries (key may include randomSeed as 3rd element)
      const previousEntries = queryClient.getQueriesData({
        queryKey: ["episodes", channelId],
      })

      const optimisticPatch = {
        // This timestamp will be slightly incorrect but it's close enough
        // because it should be almost immediately updated from the server's response.
        watch_date: new Date().toISOString(),
        verified: false,
      }

      // Optimistically update all matching cache entries
      queryClient.setQueriesData(
        { queryKey: ["episodes", channelId] },
        (oldData: any) =>
          updateEpisodeInData(oldData, episodeId, optimisticPatch),
      )
      queryClient.setQueriesData(
        { queryKey: ["episodes-preview", channelId] },
        (oldData: any) =>
          updateEpisodeInData(oldData, episodeId, optimisticPatch),
      )

      // Return a result with the snapshotted value
      return { previousEntries }
    },
    // Replace the optimistic value with the server's response on success
    onSuccess: (watchResults, episodeId) => {
      const watchData = watchResults.find(
        (watch) => watch.episode_id === episodeId,
      )
      if (watchData) {
        const patch = {
          watch_date: watchData.watch_date,
          verified: watchData.verified,
          episode_watch_id: watchData.id,
        }
        queryClient.setQueriesData(
          { queryKey: ["episodes", channelId] },
          (oldData: any) => updateEpisodeInData(oldData, episodeId, patch),
        )
        queryClient.setQueriesData(
          { queryKey: ["episodes-preview", channelId] },
          (oldData: any) => updateEpisodeInData(oldData, episodeId, patch),
        )
      }
      showSuccessToast("Episode marked as watched successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _episodeId, context) => {
      for (const [queryKey, data] of context?.previousEntries ?? []) {
        queryClient.setQueryData(queryKey, data)
      }
      const status = (error as any)?.status ?? (error as any)?.response?.status
      if (status === 409) {
        const detail =
          (error as any)?.body?.detail ??
          "Episode already has an unverified watch."
        showWarningToast(detail)
      } else {
        handleError.call(showErrorToast, error as any)
      }
    },
    // Don't invalidate/refetch episodes here — the optimistic update + onSuccess
    // already keep the cache correct, and a refetch would reset any client-side
    // reordering (e.g. "Next Episode") the user has done.
  })
}
