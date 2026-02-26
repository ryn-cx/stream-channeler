// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { ChannelsService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export function useToggleEpisodeWhitelist(
  channelId: string,
  queryChannelId: string,
) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  return useMutation({
    mutationFn: (episodeId: string) =>
      ChannelsService.swapEpisodeWhitelistStatus({
        channelId: channelId,
        episodeId,
      }),
    // When mutate is called:
    onMutate: async (episodeId, context) => {
      // Cancel any outgoing refetches
      // (so they don't overwrite our optimistic update)
      await context.client.cancelQueries({
        queryKey: ["episodes", queryChannelId],
      })

      // Snapshot the previous value
      const previousData = context.client.getQueryData([
        "episodes",
        queryChannelId,
      ])

      // Optimistically update to the new value
      context.client.setQueryData(
        ["episodes", queryChannelId],
        (oldData: any) => ({
          ...oldData,
          episodes: oldData.episodes.filter((ep: any) => ep.id !== episodeId),
        }),
      )

      // Return a result with the snapshotted value
      return { previousData }
    },
    onSuccess: () => {
      showSuccessToast("Episode whitelist status toggled successfully")
    },
    // If the mutation fails,
    // use the result returned from onMutate to roll back
    onError: (error, _episodeId, onMutateResult, context) => {
      context.client.setQueryData(
        ["episodes", queryChannelId],
        onMutateResult?.previousData,
      )
      handleError.call(showErrorToast, error as any)
    },
    // Always refetch after error or success:
    onSettled: (_data, _error, _variables, _onMutateResult, context) =>
      context.client.invalidateQueries({
        queryKey: ["episodes", queryChannelId],
      }),
  })
}
