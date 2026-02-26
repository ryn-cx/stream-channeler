// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { MediaService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export function useMarkEpisodeWatched(channelId: string | undefined) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (episodeId: string) =>
      MediaService.postWatchedEpisode({
        requestBody: {
          episode_id: episodeId,
          watch_date: new Date().toISOString(),
          verified: false,
        },
      }),
    // When mutate is called:
    onMutate: async (episodeId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({
        queryKey: ["episodes", channelId],
      })

      // Snapshot the previous value
      const previousData = context.client.getQueryData(["episodes", channelId])

      // Optimistically update to the new value
      context.client.setQueryData(["episodes", channelId], (oldData: any) => ({
        ...oldData,
        episodes: oldData.episodes.map((ep: any) =>
          ep.id === episodeId
            ? {
                ...ep,
                // This timestamp will be slightly incorrect but it's close enough
                // because it should be almost immediately updated from the server's
                // response.
                watch_date: new Date().toISOString(),
                verified: false,
              }
            : ep,
        ),
      }))

      // Return a result with the snapshotted value
      return { previousData }
    },
    // Replace the optimistic value with the server's response on success
    onSuccess: (watchData, episodeId, _onMutateResult, context) => {
      context.client.setQueryData(["episodes", channelId], (oldData: any) => ({
        ...oldData,
        episodes: oldData.episodes.map((ep: any) =>
          ep.id === episodeId
            ? {
                ...ep,
                watch_date: watchData.watch_date,
                verified: watchData.verified,
                episode_watch_id: watchData.id,
              }
            : ep,
        ),
      }))
      showSuccessToast("Episode marked as watched successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _episodeId, onMutateResult, context) => {
      context.client.setQueryData(
        ["episodes", channelId],
        onMutateResult?.previousData,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Don't invalidate/refetch episodes here — the optimistic update + onSuccess
    // already keep the cache correct, and a refetch would reset any client-side
    // reordering (e.g. "Next Episode") the user has done.
  })
}
